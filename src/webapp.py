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


class ConnectEmailRequest(BaseModel):
    provider: str = "gmail"        # gmail | outlook | icloud | custom
    email: str
    password: str                  # app password — kept in memory only
    days: int = 30


# In-memory only: credentials are never persisted; connection is used
# immediately and discarded.

IMAP_HOSTS = {
    "gmail": "imap.gmail.com",
    "outlook": "outlook.office365.com",
    "icloud": "imap.mail.me.com",
    "yahoo": "imap.mail.yahoo.com",
}


@app.post("/api/connect-email")
def connect_email(req: ConnectEmailRequest):
    """Fetch life-admin emails via IMAP into data/uploads, then auto-scan."""
    from src.ingestion.email_connector import EmailConnector

    host = IMAP_HOSTS.get(req.provider) or req.provider
    try:
        connector = EmailConnector(
            host=host, user=req.email, password=req.password
        )
        result = connector.fetch_and_save(
            save_dir=str(UPLOAD_DIR), days=req.days
        )
    except Exception as e:
        msg = str(e)
        if "AUTHENTIC" in msg.upper() or "LOGIN" in msg.upper():
            raise HTTPException(
                401,
                "Login failed. For Gmail you need an App Password "
                "(myaccount.google.com → Security → 2FA → App passwords), "
                "not your normal password.",
            )
        raise HTTPException(502, f"IMAP connection failed: {msg[:200]}")

    refresh_rag()
    # auto-scan after fetch
    files = [
        str(p) for p in sorted(UPLOAD_DIR.iterdir())
        if p.suffix.lower() in (".pdf", ".txt", ".md", ".eml")
    ]
    scan_result = get_pipeline().run(files) if files else {"tasks": [], "summary": ""}
    return {
        "fetch": result,
        "tasks": scan_result.get("tasks", []),
        "summary": scan_result.get("summary", ""),
    }


class GmailImportRequest(BaseModel):
    access_token: str
    days: int = 30


@app.post("/api/gmail-import")
def gmail_import(req: GmailImportRequest):
    """Import life-admin emails from Gmail via OAuth token (Firebase sign-in)."""
    from src.ingestion.gmail_connector import import_gmail, GmailAuthError

    try:
        result = import_gmail(
            req.access_token, save_dir=str(UPLOAD_DIR), days=req.days
        )
    except GmailAuthError as e:
        raise HTTPException(401, str(e))

    refresh_rag()
    files = [
        str(p) for p in sorted(UPLOAD_DIR.iterdir())
        if p.suffix.lower() in (".pdf", ".txt", ".md", ".eml")
    ]
    scan_result = get_pipeline().run(files) if files else {"tasks": [], "summary": ""}
    return {
        "fetch": result,
        "tasks": scan_result.get("tasks", []),
        "summary": scan_result.get("summary", ""),
    }


@app.get("/api/firebase-config")
def firebase_config():
    """Serve Firebase web config if the operator has set it up.

    Create src/web/firebase-config.json from firebase-config.example.json
    (Firebase console → Project settings → Your apps → Web app config).
    """
    config_file = Path(__file__).parent / "web" / "firebase-config.json"
    if not config_file.exists():
        return {"configured": False}
    import json
    return {"configured": True, "config": json.loads(config_file.read_text())}


@app.get("/api/health")
def health():
    gateway = build_gateway_llm() is not None
    return {"status": "ok", "llm_gateway": gateway}


@app.get("/", response_class=HTMLResponse)
def index():
    html = (Path(__file__).parent / "web" / "index.html").read_text()
    return HTMLResponse(html)
