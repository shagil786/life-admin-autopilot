# Life Admin Autopilot 🧭

**An AI agent for the boring parts of life** — built for the *Agents for Humans Hackathon* (Everyday Agents track).

It reads the documents you already have lying around (receipts, subscription emails, warranty cards, appointment notes) and proactively tells you what needs doing — **before deadlines bite**:

> *"Your Netflix renews in 3 days — cancel it?" · "Your Amazon return window closes Friday" · "Your laptop warranty expires next month"*

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
│ AGENT (Strands) │◀───▶│ RULE ENGINE       │
│ tools·drafts·  │     │ 30-day returns,   │
│ chat REPL      │     │ renewal alerts,   │
└─────────────────┘     │ warranty expiry   │
                        └────────┬─────────┘
                                 ▼
                        prioritized TASK LIST
                        + ready-to-send drafts
```

- **Ingestion** — normalizes PDFs, text files, and .eml emails into one internal format
- **Extraction** — regex + LLM extraction of vendors, amounts, dates, billing cycles, warranty lengths
- **Rule engine** — domain rules: return windows (30d), renewal alerts (7d before billing), warranty expiry (90d/30d thresholds), each producing a *priority* (urgent/high/low)
- **Strands Agent** — conversational layer that calls the pipeline as tools, explains tasks, and drafts cancellation/return messages — **never auto-sends anything** (explicit human confirmation is a hard rule)

## Quickstart

```bash
# 1. Setup
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# 2. Demo the pipeline (no API key needed — pure local rules)
python -m src.cli                # scans data/samples, prints action list

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

## Testing

```bash
pytest tests/ -v     # 42 tests: ingestion, extraction, rules, output, agent tools
```

## Architecture notes

- **Local-first**: documents never leave your machine. The LLM gateway only sees what the agent explicitly sends (task summaries, drafting requests).
- **TDD throughout**: every module test-first, 42 tests passing.
- **Pluggable models**: any OpenAI-compatible endpoint works (APInex, Token Harbor, Kira AI, local Ollama, AWS Bedrock via `BedrockModel`).

## Project structure

```
src/
├── cli.py            # one-shot pipeline CLI
├── chat.py           # conversational REPL (Strands Agent)
├── main.py           # Pipeline orchestrator
├── config.py         # TOML config
├── ingestion/        # parsers: PDF, text, email
├── extraction/        # receipt, subscription, warranty extractors
├── task_engine/      # deadline rules + priority scheduler
├── output/           # message drafter, task formatter
└── agent/            # Strands Agent, tools, prompts
```

## Roadmap

- [x] Ingestion: PDF, text
- [x] Extraction: receipts, subscriptions, warranties
- [x] Rule engine + prioritized task list
- [x] Strands Agent chat with tool calls
- [ ] Email (.eml) ingestion
- [ ] Cheaper-alternative finder (Exa search)
- [ ] LLM-powered extraction for messy scans
