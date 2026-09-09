"""Tests for text parser."""
from src.ingestion.text_parser import TextParser


def test_text_parser_reads_file(tmp_path):
    f = tmp_path / "note.txt"
    f.write_text("Amazon purchase $49.99 on 2024-01-15")
    doc = TextParser().parse(str(f))
    assert doc.type == "text"
    assert "$49.99" in doc.content
    assert doc.source == str(f)
