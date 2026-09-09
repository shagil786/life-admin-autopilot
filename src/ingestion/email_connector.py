"""IMAP email connector: fetch life-admin emails into data/uploads.

Credentials are used in-memory only — never written to disk or logs.
Requires an app password (Gmail: 2FA + app password; Outlook: app
password; others: IMAP-enabled credentials).
"""
import imaplib
import email
from email import policy
from pathlib import Path

from src.ingestion.email_parser import EmailParser

LIFE_ADMIN_KEYWORDS = [
    "receipt", "invoice", "order", "renewal", "renew", "warranty",
    "guarantee", "subscription", "bill", "billing", "payment", "charged",
    "refund", "return", "cancellation", "confirm your purchase",
    "your order", "statement", "due date", "appointment",
]

MAX_EMAIL_BYTES = 2 * 1024 * 1024  # skip giant attachments-heavy mails


def subject_matches(subject: str) -> bool:
    s = (subject or "").lower()
    return any(k in s for k in LIFE_ADMIN_KEYWORDS)


class EmailConnector:
    def __init__(self, host: str, user: str, password: str, port: int = 993):
        self._host = host
        self._user = user
        self._password = password
        self._port = port

    def _connect(self):
        client = imaplib.IMAP4_SSL(self._host, self._port)
        client.login(self._user, self._password)
        return client

    def fetch_and_save(self, save_dir: str, days: int = 30,
                       max_emails: int = 50) -> dict:
        """Fetch matching emails, save as .eml into save_dir.

        Returns {fetched, skipped, saved_names}.
        """
        client = self._connect()
        try:
            client.select("INBOX", readonly=True)

            # search for recent emails (IMAP SINCE is date-only)
            from datetime import date, timedelta
            since = (date.today() - timedelta(days=days)).strftime("%d-%b-%Y")
            status, data = client.uid("SEARCH", f'SINCE {since}')
            if status != "OK":
                return {"fetched": 0, "skipped": 0, "saved_names": []}
            uids = (data[0] or b"").split()
            # newest first
            uids = list(reversed(uids))[: max_emails * 3]

            savedir = Path(save_dir)
            savedir.mkdir(parents=True, exist_ok=True)

            fetched = 0
            skipped = 0
            saved_names = []
            for uid in uids:
                if fetched >= max_emails:
                    break
                status, msg_data = client.uid("FETCH", uid, "(RFC822)")
                if status != "OK" or not msg_data or not msg_data[0]:
                    continue
                raw = None
                for part in msg_data:
                    if isinstance(part, tuple) and len(part) >= 2:
                        raw = part[1]
                        break
                if not raw or len(raw) > MAX_EMAIL_BYTES:
                    skipped += 1
                    continue

                msg = email.message_from_bytes(raw, policy=policy.default)
                subject = str(msg.get("Subject", "") or "")
                if not subject_matches(subject):
                    skipped += 1
                    continue

                name = f"email_{uid}_{self._safe_name(subject)}.eml"
                dest = savedir / name
                dest.write_bytes(raw)
                saved_names.append(name)
                fetched += 1
            return {
                "fetched": fetched,
                "skipped": skipped,
                "saved_names": saved_names,
            }
        finally:
            try:
                client.logout()
            except Exception:
                pass

    @staticmethod
    def _safe_name(text: str) -> str:
        keep = "".join(
            c if c.isalnum() or c in "-_" else "_" for c in text.lower()
        )
        return keep[:40].strip("_") or "email"
