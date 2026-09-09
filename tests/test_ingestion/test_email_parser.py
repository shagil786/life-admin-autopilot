"""Tests for .eml email parser."""
from src.ingestion.email_parser import EmailParser


def write_eml(tmp_path, subject, body, frm="billing@netflix.com", to="me@example.com"):
    f = tmp_path / "msg.eml"
    f.write_text(
        f"From: {frm}\nTo: {to}\nSubject: {subject}\n"
        f"Content-Type: text/plain; charset=utf-8\n\n{body}\n"
    )
    return str(f)


def test_email_parser_extracts_headers_and_body(tmp_path):
    path = write_eml(
        tmp_path,
        "Your Netflix subscription renews soon",
        "Netflix subscription $15.99/month, renews 2026-09-12",
    )
    doc = EmailParser().parse(path)
    assert doc.type == "email"
    assert "Netflix" in doc.content
    assert doc.source == path


def test_email_parser_includes_subject_in_content(tmp_path):
    path = write_eml(tmp_path, "Important: renewal notice", "renews 2026-10-01")
    doc = EmailParser().parse(path)
    # Subject should be part of content so extractors can use it
    assert "renewal notice" in doc.content


def test_email_parser_handles_missing_headers(tmp_path):
    f = tmp_path / "raw.eml"
    f.write_text("Just a plain body with $29.99")
    doc = EmailParser().parse(str(f))
    assert "$29.99" in doc.content


def test_email_parser_type_email(tmp_path):
    path = write_eml(tmp_path, "s", "b")
    doc = EmailParser().parse(path)
    assert doc.type == "email"
