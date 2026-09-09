# Agent for Humans Hackathon Design

## Goal
Build a personal-operations agent that reads receipts, warranties, subscriptions, appointments, and household messages, then proactively creates actionable tasks such as returns, cancellations, renewals, scheduling, and cheaper-bill alternatives. It is unique because it connects scattered life data into a single **personal operations layer**, rather than merely summarizing documents.

## Track: Everyday Agents
Automates repetitive life tasks that nobody enjoys and everybody forgets.

## Unique Value
- **Personal Operations Layer**: ingests raw documents (PDFs, images, emails) and extracts obligations, then produces a clean, prioritized task list
- **Proactive Discovery**: surfaces deadlines before they become problems (return windows, renewal dates, subscription risks)
- **Actionable Outputs**: drafts messages, suggests alternatives, generates evidence-backed action plans
- **Privacy-First**: optional local-only processing with optional cloud integrations

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Personal Operations Agent                │
├─────────────────────┬─────────────────────┬───────────────┤
│  Ingestion Layer    │  Extraction Layer   │  Task Engine  │
│  (PDF/Image/EML)   │ (LLM + Regex +     │ (Prioritized   │
│  • Jina Reader      │   Keyword Matchers) │   Task List)   │
│  • Exa Search       │                       │               │
│  • Strands Tool     │                       │               │
├─────────────────────┼─────────────────────┼───────────────┤
│  Rule Engine        │  Output Generator   │  UI / API     │
│  (Deadline Rules)  │ (Draft Messages,   │ (CLI / Chat)   │
│  • Return Window    │   Alternatives)    │               │
│  • Renewal Alerts  │                       │               │
└─────────────────────┴─────────────────────┴───────────────┘
```

## Core Modules

### 1. Ingestion
- Accepts: PDFs, images, emails (.eml), plain text
- Uses: Strands SDK tool calls, Jina Reader for URL extraction, Exa AI for web-crawled receipts
- Normalizes to internal format: `{type, source, content, date, attachments}`

### 2. Extraction
- **Receipt parsing**: vendor, items, total, date, retailer, return policy
- **Subscription detection**: recurring amount, billing cycle, next date, cancel-by date
- **Warranty extraction**: product, purchase date, warranty length, claim window
- **Appointment parsing**: date, time, location, organizer, notes
- Uses: LLM extraction (Anthropic/Claude, Bedrock), regex fallback, domain-specific parsers

### 3. Task Engine
- **Rule-based prioritization**:
  - Return window: 30 days from purchase → "Return these headphones by Friday" (urgent)
  - Subscription renewal: 7 days before next bill → "Cancel this free trial before it renews"
  - Warranty expiry: 90 days from purchase → "Renew this warranty"
  - Appointment scheduling: "Schedule the car service"
- **Cheaper-alternative search**: Exa AI or Bedrock to find similar products at lower price
- Output: prioritized, dated task list with evidence links

### 4. Output Generator
- Drafts natural-language messages: "I noticed your Netflix trial ends July 15. Would you like me to cancel it?"
- Generates return/cancellation templates with placeholders
- Produces summary reports with evidence links

## Tech Stack

| Layer | Technology |
|-------|-----------|
| SDK | Strands Agents (Python) |
| Runtime | AWS Bedrock AgentCore (optional) / local CLI |
| LLM | Bedrock Claude 3.5 Sonnet / Anthropic API |
| Search | Exa AI, Jina Reader |
| Parsing | PyPDF2, pdfimages, regex, OCR (Tesseract optional) |
| Scheduling | iCal/Google Calendar API (optional) |
| Storage | Local JSON / S3 (optional) |

## Privacy & Safety
- **Local-first**: all processing happens on user machine by default
- **Optional cloud**: user explicitly connects email, calendar, cloud storage
- **No data exfiltration**: documents stay on device unless user opts in
- **Safe defaults**: only suggests actions after user review; never auto-executes financial/cancel actions without explicit confirmation

## Success Metrics (for demo)
- Correctly extracts obligations from 80%+ of sample receipts/subscriptions/warranties
- Generates accurate task list with < 10% false positives
- User can complete a task (return/cancel/renew) in under 60 seconds after agent suggestion
- Zero data leaves user device without explicit opt-in

## What This Is Not
- Not a generic summarizer
- Not a document repository
- Not a calendar replacement
- Not an e-commerce shopper (though it can find cheaper alternatives)

## Risks & Mitigations
| Risk | Mitigation |
|------|-----------|
| OCR/extraction errors for low-quality scans | Use multiple parsers (LLM + regex + OCR), show confidence scores, allow manual correction |
| Privacy concerns with email/cloud connections | Local-only mode by default; explicit OAuth prompts; clear opt-in/opt-out |
| Too many false-positive tasks | Configurable sensitivity; user can disable specific rule types; task review before surfacing |
| LLM cost at scale | Cache extractions; batch process; use smaller model for routine parsing, larger for synthesis |

## Next Steps (Implementation Plan)
1. Set up Strands Agents project skeleton
2. Build ingestion module (PDF/image/email acceptors)
3. Build extraction module (receipt, subscription, warranty parsers)
4. Build task engine (rule-based prioritization)
5. Build output generator (draft messages, alternatives)
6. Create demo data set and evaluate extraction accuracy
7. Package as demoable flow (CLI or simple web UI)