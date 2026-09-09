"""Tests for Gmail REST import (mocked httpx — no real API calls)."""
import base64
import httpx
import pytest

from src.ingestion.gmail_connector import import_gmail, GmailAuthError


def b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode()


def make_raw(subject, frm="billing@netflix.com"):
    return (
        f"From: {frm}\r\nTo: me@example.com\r\nSubject: {subject}\r\n"
        f"Date: Mon, 8 Sep 2026 09:00:00 +0000\r\n"
        f"Content-Type: text/plain\r\n\r\nSubscription $15.99/month\r\n"
    ).encode()


def fake_gmail_transport(messages, status_on_list=200):
    """messages: list of (id, raw_bytes)."""
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        path = url.split("?")[0]
        if path.endswith("/messages"):
            if status_on_list != 200:
                return httpx.Response(status_on_list, json={
                    "error": {"message": "Invalid Credentials"}})
            return httpx.Response(200, json={
                "messages": [{"id": mid} for mid, _ in messages],
                "resultSizeEstimate": len(messages),
            })
        # message fetch: .../messages/{id}?format=raw
        mid = path.rstrip("/").split("/")[-1]
        for m, raw in messages:
            if m == mid:
                return httpx.Response(200, json={"id": m, "raw": b64(raw)})
        return httpx.Response(404, json={"error": {"message": "not found"}})
    return httpx.MockTransport(handler)


def test_import_saves_matching_emails(tmp_path):
    msgs = [("m1", make_raw("Your Netflix renewal")), ("m2", make_raw("Order confirmed"))]
    client = httpx.Client(transport=fake_gmail_transport(msgs))
    result = import_gmail("fake-token", save_dir=str(tmp_path), client=client)
    assert result["fetched"] == 2
    saved = list(tmp_path.glob("*.eml"))
    assert len(saved) == 2
    assert b"Subject:" in saved[0].read_bytes()


def test_import_is_idempotent(tmp_path):
    msgs = [("m1", make_raw("Your Netflix renewal"))]
    client = httpx.Client(transport=fake_gmail_transport(msgs))
    first = import_gmail("t", save_dir=str(tmp_path), client=client)
    second = import_gmail("t", save_dir=str(tmp_path), client=client)
    assert first["fetched"] == 1
    assert second["fetched"] == 0  # dedup by gmail message id
    assert second["skipped"] == 1


def test_auth_error_raises(tmp_path):
    client = httpx.Client(transport=fake_gmail_transport([], status_on_list=401))
    with pytest.raises(GmailAuthError):
        import_gmail("bad-token", save_dir=str(tmp_path), client=client)


def test_empty_inbox(tmp_path):
    client = httpx.Client(transport=fake_gmail_transport([]))
    result = import_gmail("t", save_dir=str(tmp_path), client=client)
    assert result["fetched"] == 0
    assert result["saved_names"] == []


def test_respects_max_emails(tmp_path):
    msgs = [(f"m{i}", make_raw(f"Order {i}")) for i in range(10)]
    client = httpx.Client(transport=fake_gmail_transport(msgs))
    result = import_gmail("t", save_dir=str(tmp_path), max_emails=3, client=client)
    assert result["fetched"] == 3
