# Life Admin Autopilot

An AI agent for the boring parts of life, built for the Agents for Humans Hackathon (Everyday Agents track).

It reads the documents you already have lying around (receipts, subscription emails, warranty cards, appointment notes) and tells you what needs doing before deadlines bite:

> "Your Netflix renews in 3 days — cancel it?" · "Your Amazon return window closes Friday" · "Your laptop warranty expires next month"

## How it works

```
documents (.txt/.md/.pdf/.eml)
        │
        ▼
┌─────────────────┐     ┌──────────────────┐
│ INGESTION       │────▶│ EXTRACTION       │
│ PDF/text/email  │     │ vendor·amount·   │
│ parsers         │     │ dates·cycles     │
└─────────────────┘     └────────┬─────────┘
                                 │
                                 ▼
┌─────────────────┐     ┌──────────────────┐
│ AGENT (Strands) │◀───▶│ RULE ENGINE      │
│ tools·drafts·   │     │ 30-day returns,  │
│ chat REPL       │     │ renewal alerts,  │
└─────────────────┘     │ warranty expiry  │
                        └────────┬─────────┘
                                 ▼
                        prioritized TASK LIST
                        + ready-to-send drafts
```

- **Ingestion** — normalizes PDFs, text files, and .eml emails into one internal format
- **Extraction** — regex extractors for clean documents, LLM fallback for messy ones (scanned invoices, odd formats); both pull vendors, amounts, dates, billing cycles, warranty lengths
- **Rule engine** — return windows (30 days), renewal alerts (7 days before billing), warranty expiry (90/30-day thresholds); each task gets a priority (urgent/high/low)
- **RAG layer** — local hybrid retrieval (BM25 + TF-IDF) with chunk-level citations; ask "what did the Spotify email say?" and the answer quotes your document
- **Strands Agent** — conversational layer that calls the pipeline as tools, explains tasks, and drafts cancellation/return messages. It never auto-sends anything: every action needs explicit human confirmation.

## Quickstart

```bash
# 1. Setup
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# 2. Demo the pipeline (no API key needed — pure local rules)
python -m src.cli                                  # scans data/samples, prints action list
python -m src.cli --ask "when does netflix renew"  # cited Q&A over your docs

# 3. Try the agent chat (needs an OpenAI-compatible gateway)
cp .env.example .env             # fill in base URL, key, model
python -m src.chat
```

Sample agent conversation:

```
you> what needs my attention?
agent> Here's what needs your attention — 4 tasks, 2 urgent:
       🔴 Netflix — renews Sep 12 at $15.99/mo — cancel if unused
       🔴 Amazon return ($89.99) — window closes Sep 14
       🟡 Dell XPS 15 warranty expires Nov 8
       🟢 Planet Fitness — renews Oct 24
       Want me to draft a cancellation email for Netflix?

you> yes, draft it
agent> [ready-to-send draft with [ORDER ID]/[ACCOUNT EMAIL] placeholders]
```

## Evaluation

```bash
python -m src.eval_harness   # runs the labeled eval suites
```

Measured on labeled datasets (10 retrieval queries, 6 extraction documents):

- RAG retrieval: 90% hit-rate@5, MRR 0.80
- Extraction: 100% field precision and recall on clean documents (spec target was 80%)
- Messy-document extraction (LLM fallback) verified live: scanned invoice text with no clean patterns still produces the correct return-window task

## Testing

```bash
pytest tests/ -v     # 110 tests: ingestion, extraction, rules, output, agent tools, RAG, eval harness
```

## Architecture notes

- **Local-first**: documents never leave your machine. The LLM gateway only sees what the agent explicitly sends (task summaries, drafting requests).
- **TDD throughout**: every module test-first, 110 tests passing.
- **RAG is local too**: no embedding service, no vector DB — hybrid BM25 + TF-IDF runs entirely on-device.
- **Guardrails**: input filtering, tool-argument validation, turn/token limits, loop detection, and per-turn logs (prompt, tools called, tokens, latency) written to `data/agent_log.jsonl`.
- **Pluggable models**: any OpenAI-compatible endpoint works (APInex, Token Harbor, Kira AI, local Ollama, AWS Bedrock via `BedrockModel`).

## Project structure

```
src/
├── cli.py             # one-shot pipeline CLI (--ask for RAG queries)
├── chat.py            # conversational REPL (Strands Agent)
├── main.py            # Pipeline orchestrator
├── config.py          # TOML config
├── ingestion/         # parsers: PDF, text, email
├── extraction/        # receipt, subscription, warranty, LLM fallback
├── task_engine/       # deadline rules + priority scheduler + alternative finder
├── output/            # message drafter, task formatter
├── rag/               # chunker, hybrid index (BM25+TF-IDF), cited retrieval
├── eval_harness/      # labeled datasets: retrieval hit-rate/MRR, extraction precision/recall
└── agent/             # Strands Agent, tools, prompts, guardrails, observability
```

## Roadmap

- [x] Ingestion: PDF, text
- [x] Extraction: receipts, subscriptions, warranties (regex + LLM fallback)
- [x] Rule engine + prioritized task list
- [x] Strands Agent chat with tool calls
- [x] Email (.eml) ingestion
- [x] Cheaper-alternative finder (LLM-backed, pluggable search)
- [x] Local RAG: hybrid retrieval + chunk-level citations
- [x] Guardrails: input filter, arg validation, turn limits, loop detection, observability logs
- [x] Evaluation harness: retrieval (hit-rate/MRR) + extraction (precision/recall)
