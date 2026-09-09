"""Email (.eml) parser using stdlib email module."""
import email
from email import policy
from src.ingestion.base import Document, DocumentParser


class EmailParser(DocumentParser):
    """Parses .eml files into normalized Documents.

    Subject is prepended to the body so downstream extractors can use it —
    renewal/return info often lives in the subject line.
    """

    def parse(self, file_path: str) -> Document:
        with open(file_path, "rb") as f:
            msg = email.message_from_binary_file(f, policy=policy.default)

        subject = str(msg.get("Subject", "") or "")
        body = self._extract_body(msg)
        content = f"{subject}\n{body}".strip()

        return Document(
            type="email",
            content=content,
            source=file_path,
            date=self._parse_date(msg),
        )

    def _extract_body(self, msg) -> str:
        """Return the first text/plain part (or fall back to any text part)."""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    return part.get_content()
            # fallback: try any text/* part
            for part in msg.walk():
                if part.get_content_type().startswith("text/"):
                    return part.get_content()
            return ""
        try:
            return msg.get_content()
        except Exception:
            return ""

    def _parse_date(self, msg):
        from datetime import datetime

        raw = msg.get("Date")
        if not raw:
            return None
        try:
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(raw)
        except Exception:
            return None
