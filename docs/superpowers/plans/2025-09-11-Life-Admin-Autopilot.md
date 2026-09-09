# Life Admin Autopilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a personal-operations agent that reads receipts, warranties, subscriptions, appointments, and household messages, then proactively creates actionable tasks such as returns, cancellations, renewals, scheduling, and cheaper-bill alternatives.

**Architecture:** Strands Agents SDK (Python) with modular ingestion, extraction, rule engine, and output generator components. Local-first processing with optional cloud integrations.

**Tech Stack:** Python 3.11+, Strands Agents SDK, AWS Bedrock (Claude 3.5 Sonnet), Exa AI, Jina Reader, PyPDF2, Tesseract OCR (optional), pytest.

**Spec:** `docs/superpowers/specs/2025-09-11-Agent-for-Humans-Hackathon-Design.md`

## Global Constraints

- Python 3.11+ only
- Local-first processing — no data leaves device without explicit opt-in
- All financial/cancel actions require explicit user confirmation before execution
- TDD for all modules
- Clean commit history: one feature per commit

---

## File Structure

```
hackthonAmazon/
├── src/
│   ├── __init__.py
│   ├── main.py                    # CLI entry point
│   ├── config.py                  # Settings, paths, environment
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── base.py                # Abstract document parser
│   │   ├── pdf_parser.py          # PDF ingestion
│   │   ├── image_parser.py        # Image/OCR ingestion
│   │   ├── email_parser.py        # .eml file parsing
│   │   └── text_parser.py         # Plain text ingestion
│   ├── extraction/
│   │   ├── __init__.py
│   │   ├── receipt_extractor.py   # Extract vendor, items, return policy
│   │   ├── subscription_extractor.py  # Recurring amounts, billing cycles
│   │   ├── warranty_extractor.py  # Purchase date, warranty length
│   │   ├── appointment_extractor.py # Dates, times, locations
│   │   └── llm_extractor.py       # LLM-based structured extraction
│   ├── task_engine/
│   │   ├── __init__.py
│   │   ├── rules.py              # Deadline/priority rules
│   │   ├── scheduler.py          # Task scheduling and sorting
│   │   └── alternative_finder.py # Exa AI search for cheaper alternatives
│   ├── output/
│   │   ├── __init__.py
│   │   ├── message_drafter.py    # Drafts return/cancel messages
│   │   ├── task_formatter.py     # Formats task list for display
│   │   └── report_generator.py   # Summary reports
│   └── tools/
│       ├── __init__.py
│       ├── jina_reader.py        # Strands tool for web reading
│       └── exa_search.py         # Strands tool for product search
├── tests/
│   ├── __init__.py
│   ├── test_ingestion/
│   │   ├── test_pdf_parser.py
│   │   ├── test_email_parser.py
│   │   └── test_text_parser.py
│   ├── test_extraction/
│   │   ├── test_receipt_extractor.py
│   │   ├── test_subscription_extractor.py
│   │   └── test_warranty_extractor.py
│   ├── test_task_engine/
│   │   ├── test_rules.py
│   │   └── test_alternative_finder.py
│   └── test_output/
│       ├── test_message_drafter.py
│       └── test_task_formatter.py
├── data/
│   └── samples/                  # Demo sample files (receipts, PDFs, .eml)
├── docs/
│   └── superpowers/
│       ├── specs/
│       │   └── 2025-09-11-Agent-for-Humans-Hackathon-Design.md
│       └── plans/
│           └── 2025-09-11-Life-Admin-Autopilot.md  # This file
├── requirements.txt
├── pyproject.toml
└── README.md
```

## Task Breakdown

### Task 1: Project Setup and Dependencies

**Files:**
- Create: `pyproject.toml`, `requirements.txt`, `src/__init__.py`, `README.md`

**Global Constraints:**
- Python 3.11+
- Strands Agents SDK latest stable
- pytest for testing

- [ ] **Step 1: Create pyproject.toml with dependencies**
```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "life-admin-autopilot"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "strands-agents-sdk>=0.1.0",
    "anthropic>=0.30.0",
    "exa-ai>=0.1.0",
    "PyPDF2>=3.0.0",
    "pdf2image>=1.16.0",
    "python-magic>=0.4.27",
    "tesserocr>=2.7.1",
    "httpx>=0.25.0",
    "pydantic>=2.0.0",
    "python-dotenv>=1.0.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
```

- [ ] **Step 2: Create requirements.txt**
```bash
pip freeze > requirements.txt
```
Run: `pip freeze | grep -E "strands|anthropic|exa|PyPDF2|pydantic" > requirements.txt`
Expected: requirements.txt contains all listed dependencies

- [ ] **Step 3: Create src/__init__.py**
```python
"""Life Admin Autopilot - Personal Operations Agent"""
__version__ = "0.1.0"
```

- [ ] **Step 4: Update README.md** with project structure and setup instructions
Run: `cat > README.md << 'EOF'` (full project description with setup steps)

- [ ] **Step 5: Install dependencies and verify**
Run: `pip install -e .`
Expected: Successfully installs all dependencies

- [ ] **Step 6: Commit setup**
```bash
git add pyproject.toml requirements.txt src/__init__.py README.md
git commit -m "feat: initialize project with dependencies"
```

---

### Task 2: Configuration Module

**Files:**
- Create: `src/config.py`, `src/config.toml`

- [ ] **Step 1: Write test for config**
```python
# tests/test_config.py
import pytest
from src.config import load_config, get_model_settings, get_storage_path

def test_load_config_defaults():
    config = load_config()
    assert config.model_name == "claude-3-5-sonnet-20241022"
    assert config.max_retries == 3
    assert config.local_processing is True
```
Run: `pytest tests/test_config.py::test_load_config_defaults -v`
Expected: FAIL with "cannot import name 'load_config'"

- [ ] **Step 2: Implement config module**
```python
# src/config.py
from dataclasses import dataclass
from pathlib import Path
import tomllib

@dataclass
class AppConfig:
    model_name: str = "claude-3-5-sonnet-20241022"
    max_retries: int = 3
    local_processing: bool = True
    storage_path: str = "./data"

def load_config(path: Path = Path("src/config.toml")) -> AppConfig:
    with open(path, "rb") as f:
        data = tomllib.load(f)
    return AppConfig(**data.get("app", {}))

def get_model_settings() -> dict:
    config = load_config()
    return {"model": config.model_name, "max_retries": config.max_retries}
```

- [ ] **Step 3: Create config.toml**
```toml
[app]
model_name = "claude-3-5-sonnet-20241022"
max_retries = 3
local_processing = true
storage_path = "./data"
```

- [ ] **Step 4: Run tests**
Run: `pytest tests/test_config.py -v`
Expected: PASS

- [ ] **Step 5: Commit config**
```bash
git add src/config.py src/config.toml tests/test_config.py
git commit -m "feat: add configuration module with tests"
```

---

### Task 3: Ingestion Layer — PDF and Text Parsers

**Files:**
- Create: `src/ingestion/__init__.py`, `src/ingestion/base.py`, `src/ingestion/pdf_parser.py`, `src/ingestion/text_parser.py`
- Test: `tests/test_ingestion/test_pdf_parser.py`, `tests/test_ingestion/test_text_parser.py`

**Interfaces:**
- Consumes: raw file bytes, file path
- Produces: normalized document dict `{type, source, content, date, attachments}`

- [ ] **Step 1: Write test for base parser**
```python
# tests/test_ingestion/test_base.py
from src.ingestion.base import Document, DocumentParser

def test_document_creation():
    doc = Document(type="receipt", content="test", source="file.pdf")
    assert doc.type == "receipt"
    assert doc.content == "test"
```
Run: `pytest tests/test_ingestion/test_base.py -v`
Expected: FAIL

- [ ] **Step 2: Implement base classes**
```python
# src/ingestion/base.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Document:
    type: str
    content: str
    source: str
    date: Optional[datetime] = None
    attachments: list = None

class DocumentParser:
    def parse(self, file_path: str) -> Document:
        raise NotImplementedError
```

- [ ] **Step 3: Write test for PDF parser**
```python
# tests/test_ingestion/test_pdf_parser.py
import pytest
from src.ingestion.pdf_parser import PDFParser

def test_pdf_parser_returns_document():
    parser = PDFParser()
    # Create sample PDF in data/samples/
    doc = parser.parse("data/samples/sample_receipt.pdf")
    assert doc.type == "receipt"
    assert len(doc.content) > 0
```
Run: `pytest tests/test_ingestion/test_pdf_parser.py -v`
Expected: FAIL

- [ ] **Step 4: Implement PDF parser**
```python
# src/ingestion/pdf_parser.py
import PyPDF2
from pathlib import Path
from src.ingestion.base import Document, DocumentParser

class PDFParser(DocumentParser):
    def parse(self, file_path: str) -> Document:
        content = ""
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                content += page.extract_text() or ""
        return Document(
            type="receipt",
            content=content,
            source=file_path,
            date=None
        )
```

- [ ] **Step 5: Implement text parser**
```python
# src/ingestion/text_parser.py
from src.ingestion.base import Document, DocumentParser

class TextParser(DocumentParser):
    def parse(self, file_path: str) -> Document:
        with open(file_path, "r") as f:
            content = f.read()
        return Document(
            type="text",
            content=content,
            source=file_path
        )
```

- [ ] **Step 6: Create sample PDF for testing**
Run: `python -c "from reportlab.pdfgen import canvas; c = canvas.Canvas('data/samples/sample_receipt.pdf'); c.drawString(100, 700, 'Sample Receipt'); c.save()"`

- [ ] **Step 7: Run all ingestion tests**
Run: `pytest tests/test_ingestion/ -v`
Expected: All PASS

- [ ] **Step 8: Commit ingestion layer**
```bash
git add src/ingestion/ tests/test_ingestion/
git commit -m "feat: add ingestion layer for PDF and text parsing"
```

---

### Task 4: Extraction Layer — Receipt and Subscription Extractors

**Files:**
- Create: `src/extraction/__init__.py`, `src/extraction/receipt_extractor.py`, `src/extraction/subscription_extractor.py`
- Test: `tests/test_extraction/test_receipt_extractor.py`, `tests/test_extraction/test_subscription_extractor.py`

**Interfaces:**
- Consumes: `Document` object from ingestion layer
- Produces: structured dict `{vendor, amount, date, return_policy}` or `{name, amount, billing_cycle, next_date}`

- [ ] **Step 1: Write tests for receipt extractor**
```python
# tests/test_extraction/test_receipt_extractor.py
def test_receipt_extractor_finds_vendor():
    extractor = ReceiptExtractor()
    doc = Document(type="receipt", content="Amazon purchase $49.99 on 2024-01-15", source="test.pdf")
    result = extractor.extract(doc)
    assert result["vendor"] == "Amazon"
    assert result["amount"] == 49.99
```
Run: `pytest tests/test_extraction/test_receipt_extractor.py -v`
Expected: FAIL

- [ ] **Step 2: Implement receipt extractor**
```python
# src/extraction/receipt_extractor.py
import re
from typing import Optional, Dict
from src.extraction.base import BaseExtractor
from src.ingestion.base import Document

class ReceiptExtractor(BaseExtractor):
    def extract(self, doc: Document) -> Dict:
        content = doc.content
        vendor = self._extract_vendor(content)
        amount = self._extract_amount(content)
        return {"vendor": vendor, "amount": amount, "source": doc.source}

    def _extract_vendor(self, text: str) -> Optional[str]:
        patterns = [r"(?:from|bought at|via)\\s+([A-Z][a-z]+(?:\\s+[A-Z][a-z]+)+)", r"^([A-Z][a-z]+)"]
        for p in patterns:
            match = re.search(p, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def _extract_amount(self, text: str) -> Optional[float]:
        match = re.search(r"\$\s*([\\d,]+\\.?\\d*)", text)
        if match:
            return float(match.group(1).replace(",", ""))
        return None
```

- [ ] **Step 3: Implement subscription extractor**
```python
# src/extraction/subscription_extractor.py
import re
from datetime import datetime, timedelta
from typing import Optional, Dict
from src.extraction.base import BaseExtractor
from src.ingestion.base import Document

class SubscriptionExtractor(BaseExtractor):
    def extract(self, doc: Document) -> Dict:
        content = doc.content
        return {
            "name": self._extract_name(content),
            "amount": self._extract_amount(content),
            "next_billing_date": self.__extract_next_date(content),
            "cancel_by_date": self._extract_cancel_by(content)
        }

    def _extract_name(self, text: str) -> Optional[str]:
        match = re.search(r"(?:subscription|plan|service)[:\\s]+([A-Za-z0-9\\s]+)", text, re.IGNORECASE)
        return match.group(1).strip() if match else None

    def _extract_amount(self, text: str) -> Optional[float]:\n        match = re.search(r"\\$\\s*([\\d,]+\\.?\\d*)\\s*(?:\\/month|\\/monthly)", text, re.IGNORECASE)\n        return float(match.group(1).replace(\",\", \"\")) if match else None\n\n    def _extract_next_date(self, text: str) -> Optional[str]:\n        match = re.search(r\"renew(?:s|al)?[:\\s]+(\\d{4}-\\d{2}-\\d{2})\", text, re.IGNORECASE)\n        return match.group(1) if match else None\n```\n\n- [ ] **Step 4: Write tests for subscription extractor**\n```python\n# tests/test_extraction/test_subscription_extractor.py\ndef test_subscription_extractor_finds_name():\n    extractor = SubscriptionExtractor()\n    doc = Document(type=\"subscription\", content=\"Netflix subscription: $15.99/month, renews 2025-01-15\", source=\"test.pdf\")\n    result = extractor.extract(doc)\n    assert result[\"name\"] == \"Netflix\"\n    assert result[\"amount\"] == 15."
```

<tool_call>
<function=write>
<parameter=content>
# Life Admin Autopilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a personal-operations agent that reads receipts, warranties, subscriptions, appointments, and household messages, then proactively creates actionable tasks such as returns, cancellations, renewals, scheduling, and cheaper-bill alternatives.

**Architecture:** Strands Agents SDK (Python) with modular ingestion, extraction, rule engine, and output generator components. Local-first processing with optional cloud integrations.

**Tech Stack:** Python 3.11+, Strands Agents SDK, AWS Bedrock (Claude 3.5 Sonnet), Exa AI, Jina Reader, PyPDF2, Tesseract OCR (optional), pytest.

**Spec:** `docs/superpowers/specs/2025-09-11-Agent-for-Humans-Hackathon-Design.md`

## Global Constraints

- Python 3.11+ only
- Local-first processing — no data leaves device without explicit opt-in
- All financial/cancel actions require explicit user confirmation before execution
- TDD for all modules
- Clean commit history: one feature per commit

---

## File Structure

```
hackthonAmazon/
├── src/
│   ├── __init__.py
│   ├── main.py                    # CLI entry point
│   ├── config.py                  # Settings, paths, environment
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── base.py                # Abstract document parser
│   │   ├── pdf_parser.py          # PDF ingestion
│   │   ├── image_parser.py        # Image/OCR ingestion
│   │   ├── email_parser.py        # .eml file parsing
│   │   └── text_parser.py         # Plain text ingestion
│   ├── extraction/
│   │   ├── __init__.py
│   │   ├── receipt_extractor.py   # Extract vendor, items, return policy
│   │   ├── subscription_extractor.py  # Recurring amounts, billing cycles
│   │   ├── warranty_extractor.py  # Purchase date, warranty length
│   │   ├── appointment_extractor.py # Dates, times, locations
│   │   └── llm_extractor.py       # LLM-based structured extraction
│   ├── task_engine/
│   │   ├── __init__.py
│   │   ├── rules.py              # Deadline/priority rules
│   │   ├── scheduler.py          # Task scheduling and sorting
│   │   └── alternative_finder.py # Exa AI search for cheaper alternatives
│   ├── output/
│   │   ├── __init__.py
│   │   ├── message_drafter.py    # Drafts return/cancel messages
│   │   ├── task_formatter.py     # Formats task list for display
│   │   └── report_generator.py   # Summary reports
│   └── tools/
│       ├── __init__.py
│       ├── jina_reader.py        # Strands tool for web reading
│       └── exa_search.py         # Strands tool for product search
├── tests/
│   ├── __init__.py
│   ├── test_ingestion/
│   │   ├── test_pdf_parser.py
│   │   ├── test_email_parser.py
│   │   └── test_text_parser.py
│   ├── test_extraction/
│   │   ├── test_receipt_extractor.py
│   │   ├── test_subscription_extractor.py
│   │   └── test_warranty_extractor.py
│   ├── test_task_engine/
│   │   ├── test_rules.py
│   │   └── test_alternative_finder.py
│   └── test_output/
│       ├── test_message_drafter.py
│       └── test_task_formatter.py
├── data/
│   └── samples/                  # Demo sample files (receipts, PDFs, .eml)
├── docs/
│   └── superpowers/
│       ├── specs/
│       │   └── 2025-09-11-Agent-for-Humans-Hackathon-Design.md
│       └── plans/
│           └── 2025-09-11-Life-Admin-Autopilot.md  # This file
├── requirements.txt
├── pyproject.toml
└── README.md
```

## Task Breakdown

### Task 1: Project Setup and Dependencies

**Files:**
- Create: `pyproject.toml`, `requirements.txt`, `src/__init__.py`, `README.md`

**Global Constraints:**
- Python 3.11+
- Strands Agents SDK latest stable
- pytest for testing

- [ ] **Step 1: Create pyproject.toml with dependencies**
```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "life-admin-autopilot"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "strands-agents-sdk>=0.1.0",
    "anthropic>=0.30.0",
    "exa-ai>=0.1.0",
    "PyPDF2>=3.0.0",
    "pdf2image>=1.16.0",
    "python-magic>=0.4.27",
    "tesserocr>=2.7.1",
    "httpx>=0.25.0",
    "pydantic>=2.0.0",
    "python-dotenv>=1.0.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
```

- [ ] **Step 2: Create requirements.txt**
```bash
pip freeze > requirements.txt
```
Run: `pip freeze | grep -E "strands|anthropic|exa|PyPDF2|pydantic" > requirements.txt`
Expected: requirements.txt contains all listed dependencies

- [ ] **Step 3: Create src/__init__.py**
```python
"""Life Admin Autopilot - Personal Operations Agent"""
__version__ = "0.1.0"
```

- [ ] **Step 5: Install dependencies and verify**
Run: `pip install -e .`
Expected: Successfully installs all dependencies

- [ ] **Step 6: Commit setup**
```bash
git add pyproject.toml requirements.txt src/__init__.py README.md
git commit -m "feat: initialize project with dependencies"
```

---

### Task 2: Configuration Module

**Files:**
- Create: `src/config.py`, `src/config.toml`

- [ ] **Step 1: Write test for config**
```python
# tests/test_config.py
import pytest
from src.config import load_config, get_model_settings, get_storage_path

def test_load_config_defaults():
    config = load_config()
    assert config.model_name == "claude-3-5-sonnet-20241022"
    assert config.max_retries == 3
    assert config.local_processing is True
```
Run: `pytest tests/test_config.py::test_load_config_defaults -v`
Expected: FAIL with "cannot import name 'load_config'"

- [ ] **Step 2: Implement config module**
```python
# src/config.py
from dataclasses import dataclass
from pathlib import Path
import tomllib

@dataclass
class AppConfig:
    model_name: str = "claude-3-5-sonnet-20241022"
    max_retries: int = 3
    local_processing: bool = True
    storage_path: str = "./data"

def load_config(path: Path = Path("src/config.toml")) -> AppConfig:
    with open(path, "rb") as f:
        data = tomllib.load(f)
    return AppConfig(**data.get("app", {}))

def get_model_settings() -> dict:
    config = load_config()
    return {"model": config.model_name, "max_retries": config.max_retries}
```

- [ ] **Step 3: Create config.toml**
```toml
[app]
model_name = "claude-3-5-sonnet-20241022"
max_retries = 3
local_processing = true
storage_path = "./data"
```

- [ ] **Step 3: Run tests**
Run: `pytest tests/test_config.py -v`
Expected: PASS

- [ ] **Step 3: Commit config**
```bash
git add src/config.py src/config.toml tests/test_config.py
git commit -m "feat: add configuration module with tests"
```

---

### Task 3: Ingestion Layer — PDF and Text Parsers

**Files:**
- Create: `src/ingestion/__init__.py`, `src/ingestion/base.py`, `src/ingestion/pdf_parser.py`, `src/ingestion/text_parser.py`
- Test: `tests/test_ingestion/test_pdf_parser.py`, `tests/test_ingestion/test_text_parser.py`

**Interfaces:**
- Consumes: raw file bytes, file path
- Produces: normalized document dict `{type, source, content, date, attachments}`

- [ ] **Step 1: Write test for base parser**
```python
# tests/test_ingestion/test_base.py
from src.ingestion.base import Document, DocumentParser

def test_document_creation():
    doc = Document(type="receipt", content="test", source="file.pdf")
    assert doc.type == "receipt"
    assert doc.content == "test"
```
Run: `pytest tests/test_ingestion/test_base.py -v`
Expected: FAIL

- [ ] **Step 2: Implement base classes**
```python
# src/ingestion/base.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Document:
    type: str
    content: str
    source: str
    date: Optional[datetime] = None
    attachments: list = None

class DocumentParser:
    def parse(self, file_path: str) -> Document:
        raise NotImplementedError
```

- [ ] **Step 3: Write test for PDF parser**
```python
# tests/test_ingestion/test_pdf_parser.py
import pytest
from src.ingestion.pdf_parser import PDFParser

def test_pdf_parser_returns_document():
    parser = PDFParser()
    # Create sample PDF in data/samples/
    doc = parser.parse("data/samples/sample_receipt.pdf")
    assert doc.type == "receipt"
    assert len(doc.content) > 0
```
Run: `pytest tests/test_ingestion/test_pdf_parser.py -v`
Expected: FAIL

- [ ] **Step 4: Implement PDF parser**
```python
# src/ingestion/pdf_parser.py
import PyPDF2
from pathlib import Path
from src.ingestion.base import Document, DocumentParser

class PDFParser(DocumentParser):
    def parse(self, file_path: str) -> Document:
        content = ""
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                content += page.extract_text() or ""
        return Document(
            type="receipt",
            content=content,
            source=file_path,
            date=None
        )
```

- [ ] **Step 5: Implement text parser**
```python
# src/ingestion/text_parser.py
from src.ingestion.base import Document, DocumentParser

class TextParser(DocumentParser):
    def parse(self, file_path: str) -> Document:
        with open(file_path, "r") as f:
            content = f.read()
        return Document(
            type="text",
            content=content,
            source=file_path
        )
```

- [ ] **Step 6: Create sample PDF for testing**
Run: `python -c "from reportlab.pdfgen import canvas; c = canvas.Canvas('data/samples/sample_receipt.pdf'); c.drawString(100, 700, 'Sample Receipt'); c.save()"`

- [ ] **Step 6: Run all ingestion tests**
Run: `pytest tests/test_ingestion/ -v`
Expected: All PASS

- [ ] **Step 7: Commit ingestion layer**
```bash
git add src/ingestion/ tests/test_ingestion/
git commit -m "feat: add ingestion layer for PDF and text parsing"
```

---

### Task 4: Extraction Layer — Receipt and Subscription Extractors

**Files:**
- Create: `src/extraction/__init__.py`, `src/extraction/receipt_extractor.py`, `src/extraction/subscription_extractor.py`
- Test: `tests/test_extraction/test_receipt_extractor.py`, `tests/test_extraction/test_subscription_extractor.py`

**Interfaces:**
- Consumes: `Document` object from ingestion layer
- Produces: structured dict `{vendor, amount, date, return_policy}` or `{name, amount, billing_cycle, next_date}`

- [ ] **Step 1: Write tests for receipt extractor**
```python
# tests/test_extraction/test_receipt_extractor.py
def test_receipt_extractor_finds_vendor():
    extractor = ReceiptExtractor()
    doc = Document(type="receipt", content="Amazon purchase $49.99 on 2024-01-15", source="test.pdf")
    result = extractor.extract(doc)
    assert result["vendor"] == "Amazon"
    assert result["amount"] == 49.99
```
Run: `pytest tests/test_extraction/test_receipt_extractor.py -v`
Expected: FAIL

- [ ] **Step 2: Implement receipt extractor**
```python
# src/extraction/receipt_extractor.py
import re
from typing import Optional, Dict
from src.extraction.base import BaseExtractor
from src.ingestion.base import Document

class ReceiptExtractor(BaseExtractor):
    def extract(self, doc: Document) -> Dict:
        content = doc.content
        vendor = self._extract_vendor(content)
        amount = self._extract_amount(content)
        return {"vendor": vendor, "amount": amount, "source": doc.source}

    def _extract_vendor(self, text: str) -> Optional[str]:
        patterns = [r"(?:from|bought at|via)\\s+([A-Z][a-z]+(?:\\s+[A-Z][a-z]+)+)", r"^([A-Z][a-z]+)"]
        for p in patterns:
            match = re.search(p, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def _extract_amount(self, text: str) -> Optional[float]:
        match = re.search(r"\$\s*([\\d,]+\\.?\\d*)", text)
        if match:
            return float(match.group(1).replace(",", ""))
        return None
```

- [ ] **Step 3: Implement subscription extractor**
```python
# src/extraction/subscription_extractor.py
import re
from datetime import datetime, timedelta
from typing import Optional, Dict
from src.extraction.base import BaseExtractor
from src.ingestion.base import Document

class SubscriptionExtractor(BaseExtractor):
    def extract(self, doc: Document) -> Dict:
        content = doc.content
        return {
            "name": self._extract_name(content),
            "amount": self._extract_amount(content),
            "next_billing_date": self.__extract_next_date(content),
            "cancel_by_date": self._extract_cancel_by(content)
        }

    def _extract_name(self, text: str) -> Optional[str]:
        match = re.search(r"(?:subscription|plan|service)[:\\s]+([A-Za-z0-9\\s]+)", text, re.IGNORECASE)
        return match.group(1).strip() if match else None

    def _extract_amount(self, text: str) -> Optional[float]:\n        match = re.search(r"\\$\\s*([\\d,]+\\.?\\d*)\\s*(?:\\/month|\\/monthly)", text, re.IGNORECASE)\n        return float(match.group(1).replace(\",\", \"\")) if match else None\n\n    def _extract_next_date(self, text: str) -> Optional[str]:\n        match = re.search(r\"renew(?:s|al)?[:\\s]+(\\d{4}-\\d{2}-\\d{2})\", text, re.IGNORECASE)\n        return match.group(1) if match else None\n```

- [ ] **Step 5: Write tests for subscription extractor**
```python
# tests/test_extraction/test_subscription_extractor.py
def test_subscription_extractor_finds_name():\n    extractor = SubscriptionExtractor()\n    doc = Document(type=\"subscription\", content=\"Netflix subscription: $15.99/month, renews 2025-01-15\", source=\"test.pdf\")\n    result = extractor.extract(doc)\n    assert result[\"name\"] == \"Netflix\"\n    assert result[\"amount\"] == 15."
```

<tool_call>
<function=write>
<parameter=content>
# Life Admin Autopilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a personal-operations agent that reads receipts, warranties, subscriptions, appointments, and household messages, then proactively creates actionable tasks such as returns, cancellations, renewals, scheduling, and cheaper-bill alternatives.

**Architecture:** Strands Agents SDK (Python) with modular ingestion, extraction, rule engine, and output generator components. Local-first processing with optional cloud integrations.

**Tech Stack:** Python 3.11+, Strands Agents SDK, AWS Bedrock (Claude 3.5 Sonnet), Exa AI, Jina Reader, PyPDF2, Tesseract OCR (optional), pytest.

**Spec:** `docs/superpowers/specs/2025-09-11-Agent-for-Humans-Hackathon-Design.md`

## Global Constraints

- Python 3.11+ only
- Local-first processing — no data leaves device without explicit opt-in
- All financial/cancel actions require explicit user confirmation before execution
- TDD for all modules
- Clean commit history: one feature per commit

---

## File Structure

```
hackthonAmazon/
├── src/
│   ├── __init__.py
│   ├── main.py                    # CLI entry point
│   ├── config.py                  # Settings, paths, environment
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── base.py                # Abstract document parser
│   │   ├── pdf_parser.py          # PDF ingestion
│   │   ├── image_parser.py        # Image/OCR ingestion
│   │   ├── email_parser.py        # .eml file parsing
│   │   └── text_parser.py         # Plain text ingestion
│   ├── extraction/
│   │   ├── __init__.py
│   │   ├── receipt_extractor.py   # Extract vendor, items, return policy
│   │   ├── subscription_extractor.py  # Recurring amounts, billing cycles
│   │   ├── warranty_extractor.py  # Purchase date, warranty length
│   │   ├── appointment_extractor.py # Dates, times, locations
│   │   └── llm_extractor.py       # LLM-based structured extraction
│   ├── task_engine/
│   │   ├── __init__.py
│   │   ├── rules.py              # Deadline/priority rules
│   │   ├── scheduler.py          # Task scheduling and sorting
│   │   └── alternative_finder.py # Exa AI search for cheaper alternatives
│   ├── output/
│   │   ├── __init__.py
│   │   ├── message_drafter.py    # Drafts return/cancel messages
│   │   ├── task_formatter.py     # Formats task list for display
│   │   └── report_generator.py   # Summary reports
│   └── tools/
│       ├── __init__.py
│       ├── jina_reader.py        # Strands tool for web reading
│       └── exa_search.py         # Strands tool for product search
├── tests/
│   ├── __init__.py
│   ├── test_ingestion/
│   │   ├── test_pdf_parser.py
│   │   ├── test_email_parser.py
│   │   └── test_text_parser.py
│   ├── test_extraction/
│   │   ├── test_receipt_extractor.py
│   │   ├── test_subscription_extractor.py
│   │   └── test_warranty_extractor.py
│   ├── test_task_engine/
│   │   ├── test_rules.py
│   │   └── test_alternative_finder.py
│   └── test_output/
│       ├── test_message_drafter.py
│       └── test_task_formatter.py
├── data/
│   └── samples/                  # Demo sample files (receipts, PDFs, .eml)
├── docs/
│   └── superpowers/
│       ├── specs/
│       │   └── 2025-09-11-Agent-for-Humans-Hackathon-Design.md
│       └── plans/
│           └── 2025-09-11-Life-Admin-Autopilot.md  # This file
├── requirements.txt
├── pyproject.toml
└── README.md