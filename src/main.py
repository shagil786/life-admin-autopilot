"""Main pipeline: ingest documents -> extract obligations -> generate tasks."""
from pathlib import Path
from src.ingestion.pdf_parser import PDFParser
from src.ingestion.text_parser import TextParser
from src.ingestion.email_parser import EmailParser
from src.extraction.receipt_extractor import ReceiptExtractor
from src.extraction.subscription_extractor import SubscriptionExtractor
from src.extraction.warranty_extractor import WarrantyExtractor
from src.extraction.llm_extractor import LLMExtractor
from src.extraction.base import BaseExtractor
from src.task_engine.rules import RuleEngine
from src.task_engine.scheduler import TaskScheduler
from src.output.task_formatter import format_tasks, format_summary


class Pipeline:
    """End-to-end personal operations pipeline."""

    def __init__(self, rules: RuleEngine = None, scheduler: TaskScheduler = None,
                 llm=None):
        self.rules = rules
        self.scheduler = scheduler
        self.llm = llm  # optional CompletionLLM for fallback extraction
        self.parsers = {
            ".pdf": PDFParser(),
            ".txt": TextParser(),
            ".md": TextParser(),
            ".eml": EmailParser(),
        }
        self.extractors = [
            ReceiptExtractor(),
            SubscriptionExtractor(),
            WarrantyExtractor(),
        ]
        self.llm_extractor = LLMExtractor(llm=llm) if llm else None

    def run(self, files: list) -> dict:
        """Process files and return {tasks, summary, formatted}."""
        all_tasks = []
        for file_path in files:
            path = Path(file_path)
            parser = self.parsers.get(path.suffix.lower())
            if not parser:
                continue
            doc = parser.parse(str(path))
            produced = 0
            for extractor in self.extractors:
                data = extractor.extract(doc)
                if self._is_relevant(extractor, data):
                    tasks = self._evaluate(extractor, data)
                    produced += len(tasks)
                    all_tasks.extend(tasks)
            # Fallback: regex produced no tasks -> try the LLM
            if produced == 0 and self.llm_extractor:
                data = self.llm_extractor.extract(doc)
                all_tasks.extend(self._evaluate_extracted(data))
        ordered = self.scheduler.sort(all_tasks) if self.scheduler else all_tasks
        return {
            "tasks": ordered,
            "summary": format_summary(ordered),
            "formatted": format_tasks(ordered),
        }

    def _evaluate_extracted(self, data: dict) -> list:
        """Route generic LLM-extracted data to the right rule evaluator."""
        tasks = []
        if not self.rules:
            return tasks
        # Subscription-like: has renewal/billing info
        if data.get("next_billing_date") or data.get("billing_cycle"):
            sub = {
                "name": data.get("vendor") or data.get("product"),
                "amount": data.get("amount"),
                "billing_cycle": data.get("billing_cycle"),
                "next_billing_date": data.get("next_billing_date"),
            }
            tasks.extend(self.rules.evaluate_subscription(sub))
        # Warranty-like: product + warranty length
        elif data.get("warranty_years") and data.get("product"):
            from datetime import date, timedelta
            purchase = data.get("date")
            try:
                start = date.fromisoformat(purchase)
                expires = start.replace(year=start.year + int(data["warranty_years"]))
                expires_str = expires.isoformat()
            except (TypeError, ValueError):
                expires_str = None
            tasks.extend(self.rules.evaluate_warranty({
                "product": data["product"],
                "purchase_date": purchase,
                "warranty_years": data["warranty_years"],
                "warranty_expires": expires_str,
            }))
        # Receipt-like: vendor + amount + purchase date
        elif data.get("amount") and (data.get("vendor") or data.get("date")):
            tasks.extend(self.rules.evaluate_receipt({
                "vendor": data.get("vendor"),
                "amount": data.get("amount"),
                "date": data.get("date"),
            }))
        return tasks

    def _is_relevant(self, extractor, data: dict) -> bool:
        # A receipt extractor result with no amount and no vendor is noise
        from src.extraction.receipt_extractor import ReceiptExtractor
        if isinstance(extractor, ReceiptExtractor):
            return bool(data.get("amount") or data.get("date"))
        return True

    def _evaluate(self, extractor, data: dict) -> list:
        from src.extraction.receipt_extractor import ReceiptExtractor
        from src.extraction.subscription_extractor import SubscriptionExtractor
        from src.extraction.warranty_extractor import WarrantyExtractor
        if not self.rules:
            return []
        if isinstance(extractor, ReceiptExtractor):
            return self.rules.evaluate_receipt(data)
        if isinstance(extractor, SubscriptionExtractor):
            return self.rules.evaluate_subscription(data)
        if isinstance(extractor, WarrantyExtractor):
            return self.rules.evaluate_warranty(data)
        return []
