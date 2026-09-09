"""Main pipeline: ingest documents -> extract obligations -> generate tasks."""
from pathlib import Path
from src.ingestion.pdf_parser import PDFParser
from src.ingestion.text_parser import TextParser
from src.ingestion.email_parser import EmailParser
from src.extraction.receipt_extractor import ReceiptExtractor
from src.extraction.subscription_extractor import SubscriptionExtractor
from src.extraction.warranty_extractor import WarrantyExtractor
from src.task_engine.rules import RuleEngine
from src.task_engine.scheduler import TaskScheduler
from src.output.task_formatter import format_tasks, format_summary


class Pipeline:
    """End-to-end personal operations pipeline."""

    def __init__(self, rules: RuleEngine = None, scheduler: TaskScheduler = None):
        self.rules = rules
        self.scheduler = scheduler
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

    def run(self, files: list) -> dict:
        """Process files and return {tasks, summary, formatted}."""
        all_tasks = []
        for file_path in files:
            path = Path(file_path)
            parser = self.parsers.get(path.suffix.lower())
            if not parser:
                continue
            doc = parser.parse(str(path))
            for extractor in self.extractors:
                data = extractor.extract(doc)
                if self._is_relevant(extractor, data):
                    all_tasks.extend(self._evaluate(extractor, data))
        ordered = self.scheduler.sort(all_tasks) if self.scheduler else all_tasks
        return {
            "tasks": ordered,
            "summary": format_summary(ordered),
            "formatted": format_tasks(ordered),
        }

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
