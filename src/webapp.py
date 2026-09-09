"""Web API: exposes the pipeline, RAG, and agent over HTTP for the frontend."""
import tempfile
from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from src.main import Pipeline
from src.extraction.gateway_llm import build_gateway_llm
from src.task_engine.rules import RuleEngine
from src.task_engine.scheduler import TaskScheduler
from src.rag.service import RagService

app = FastAPI(title="Life Admin Autopilot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

_pipeline = None
_rag = None


def get_pipeline() -> Pipeline:
    global _pipeline
    if _pipeline is None:
        today = date.today()
        _pipeline = Pipeline(
            rules=RuleEngine(today=today),
            scheduler=TaskScheduler(today=today),
            llm=build_gateway_llm(),
        )
    return _pipeline


def get_rag() -> RagService:
    global _rag
    if _rag is None:
        _rag = RagService(samples_dir="data/uploads")
        _rag.ingest()
    return _rag


def refresh_rag():
    global _rag
    _rag = RagService(samples_dir="data/uploads")
    _rag.ingest()


@app.post("/api/scan")
def scan():
    """Run the pipeline over uploaded documents, return tasks."""
    files = [
        str(p) for p in sorted(UPLOAD_DIR.iterdir())
        if p.suffix.lower() in (".pdf", ".txt", ".md", ".eml")
    ]
    if not files:
        return {"tasks": [], "summary": "No documents yet — upload some!"}
    result = get_pipeline().run(files)
    return {"tasks": result["tasks"], "summary": result["summary"]}


@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    """Save an uploaded document into data/uploads."""
    suffix = Path(file.filename or "doc.txt").suffix.lower()
    if suffix not in (".pdf", ".txt", ".md", ".eml"):
        raise HTTPException(400, f"Unsupported file type: {suffix}")
    dest = UPLOAD_DIR / (file.filename or "doc.txt")
    content = await file.read()
    dest.write_bytes(content)
    refresh_rag()
    return {"saved": str(dest), "size": len(content)}


class AskRequest(BaseModel):
    question: str


@app.post("/api/ask")
def ask(req: AskRequest):
    """RAG query over uploaded documents with citations."""
    if not get_rag().index.size:
        return {"answer": None, "chunks": [],
                "message": "No documents indexed yet — upload some first."}
    results = get_rag().query(req.question, top_k=5)
    if not results:
        return {"answer": None, "chunks": [],
                "message": f"Nothing matched {req.question!r}."}
    return {
        "answer": None,  # frontend renders chunks; agent tab does LLM answers
        "chunks": [
            {"citation": r["citation"], "text": r["chunk"]["text"],
             "score": r["score"], "doc_type": r["chunk"].get("doc_type")}
            for r in results
        ],
        "message": None,
    }


class ChatRequest(BaseModel):
    message: str


@app.post("/api/chat")
def chat(req: ChatRequest):
    """One-shot agent turn (no streaming) for the frontend chat."""
    from src.agent.guardrails import check_input, MAX_TURNS
    from src.agent.model_factory import build_agent, get_model_id
    from src.agent.prompts import SYSTEM_PROMPT
    from src.agent.tools import (
        scan_documents, draft_action_message, find_cheaper_alternatives,
        search_documents, get_today, set_active_turn_log,
    )
    from src.agent.observe import TurnLog
    from strands.types.agent import Limits

    ok, reason = check_input(req.message)
    if not ok:
        return {"reply": reason, "tools_used": []}

    turn = TurnLog(prompt=req.message, model=get_model_id())
    set_active_turn_log(turn)
    try:
        agent = build_agent(
            SYSTEM_PROMPT,
            tools=[scan_documents, draft_action_message,
                   find_cheaper_alternatives, search_documents, get_today],
        )
        # point the tools at the uploads dir for the web context
        result = agent(
            req.message,
            limits=Limits(turns=MAX_TURNS, output_tokens=4096),
        )
        reply = str(result)
    except Exception as e:
        reply = f"(agent error: {e})"
    finally:
        set_active_turn_log(None)
    return {
        "reply": reply,
        "tools_used": [
            {"tool": t["tool"], "args": t["args"], "ok": t["ok"]}
            for t in turn.tool_calls
        ],
    }


@app.get("/api/health")
def health():
    gateway = build_gateway_llm() is not None
    return {"status": "ok", "llm_gateway": gateway}


@app.get("/", response_class=HTMLResponse)
def index():
    html = (Path(__file__).parent / "web" / "index.html").read_text()
    return HTMLResponse(html)
