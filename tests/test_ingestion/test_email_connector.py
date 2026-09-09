"""Tests for the email connector (mocked IMAP — no real server)."""
import pytest
from unittest.mock import MagicMock

from src.ingestion.email_connector import (
    EmailConnector,
    LIFE_ADMIN_KEYWORDS,
    subject_matches,
)


def make_raw_email(subject, frm="billing@netflix.com", body="sub $15.99"):
    return (
        f"From: {frm}\r\nTo: me@example.com\r\nSubject: {subject}\r\n"
        f"Date: Mon, 8 Sep 2026 09:00:00 +0000\r\n"
        f"Content-Type: text/plain\r\n\r\n{body}\r\n"
    ).encode()


class FakeIMAP:
    """Mimics the imaplib calls EmailConnector uses."""

    def __init__(self, messages):
        # messages: list of (uid, raw_bytes)
        self._messages = messages
        self.fetched_uids = []
        self._selected = None

    def login(self, user, password):
        if password == "bad":
            raise Exception("AUTHENTICATIONFAILED")
        return ("OK", [b"Logged in"])

    def select(self, folder, **kwargs):
        self._selected = folder
        return ("OK", [str(len(self._messages)).encode()])

    def uid(self, command, *args):
        if command == "SEARCH":
            # return all uids as b"1 2 3 ..."
            uids = " ".join(str(u) for u, _ in self._messages)
            return ("OK", [uids.encode()])
        if command == "FETCH":
            uid = int(args[0])
            self.fetched_uids.append(uid)
            for u, raw in self._messages:
                if u == uid:
                    return ("OK", [(b"1 (UID 1 RFC822)", raw), b")"])
        return ("NO", [b"unsupported"])

    def logout(self):
        return ("BYE", [b"Bye"])


def test_subject_matches_life_admin():
    assert subject_matches("Your Netflix renewal is coming")
    assert subject_matches("Order confirmed: Sony headphones")
    assert subject_matches("Invoice #4471 from ACME")
    assert subject_matches("Your warranty is expiring")
    assert not subject_matches("Weekly newsletter")
    assert not subject_matches("Meeting notes")


def test_connector_saves_matching_emails(tmp_path, monkeypatch):
    msgs = [
        (1, make_raw_email("Your Netflix renewal")),      # match
        (2, make_raw_email("Happy birthday!")),           # no match
        (3, make_raw_email("Order confirmed: headphones")),  # match
    ]
    fake = FakeIMAP(msgs)

    connector = EmailConnector(
        host="fake.imap", user="me@test.com", password="app-pass"
    )
    monkeypatch.setattr(connector, "_connect", lambda: fake)

    result = connector.fetch_and_save(save_dir=str(tmp_path), days=30)

    # only matching subjects saved as .eml
    saved = sorted(p.name for p in tmp_path.glob("*.eml"))
    assert len(saved) == 2
    assert result["fetched"] == 2
    assert result["skipped"] == 1
    # saved files parse as emails with subjects intact
    content = (tmp_path / saved[0]).read_bytes()
    assert b"Subject:" in content


def test_connector_auth_failure_raises(tmp_path, monkeypatch):
    fake = FakeIMAP([])
    connector = EmailConnector(
        host="fake.imap", user="me@test.com", password="bad"
    )

    def fake_connect():
        fake.login("me@test.com", "bad")  # raises AUTHENTICATIONFAILED
        return fake

    monkeypatch.setattr(connector, "_connect", fake_connect)
    with pytest.raises(Exception):
        connector.fetch_and_save(save_dir=str(tmp_path))


def test_connector_respects_limit(tmp_path, monkeypatch):
    msgs = [(i, make_raw_email(f"Order {i}")) for i in range(1, 8)]  # 7 matches
    fake = FakeIMAP(msgs)
    connector = EmailConnector(
        host="fake.imap", user="me@test.com", password="ok"
    )
    monkeypatch.setattr(connector, "_connect", lambda: fake)
    result = connector.fetch_and_save(save_dir=str(tmp_path), max_emails=5)
    assert result["fetched"] == 5


def test_keywords_cover_core_domains():
    for word in ["receipt", "invoice", "renewal", "warranty", "order",
                 "bill", "payment", "subscription", "refund"]:
        assert any(word in k for k in LIFE_ADMIN_KEYWORDS)
