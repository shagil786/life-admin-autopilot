"""Tests for alternative finder (offline — mock the search fn)."""
from src.task_engine.alternative_finder import AlternativeFinder


def test_returns_no_alternatives_when_no_provider():
    finder = AlternativeFinder(search_fn=None)
    result = finder.find("Sony WH-1000XM4 headphones", max_price=89.99)
    assert result == []


def test_uses_injected_search_fn():
    def fake_search(product, max_price):
        return [
            {"name": "Anker Soundcore Q45", "price": 79.99,
             "why": "similar ANC, 50h battery"},
        ]

    finder = AlternativeFinder(search_fn=fake_search)
    result = finder.find("Sony WH-1000XM4 headphones", max_price=89.99)
    assert len(result) == 1
    assert result[0]["name"] == "Anker Soundcore Q45"
    assert result[0]["price"] == 79.99


def test_alternatives_sorted_by_price():
    def fake_search(product, max_price):
        return [
            {"name": "B", "price": 60.0, "why": ""},
            {"name": "A", "price": 50.0, "why": ""},
            {"name": "C", "price": 70.0, "why": ""},
        ]

    finder = AlternativeFinder(search_fn=fake_search)
    result = finder.find("widget", max_price=89.99)
    prices = [r["price"] for r in result]
    assert prices == sorted(prices)
    assert prices[0] == 50.0


def test_alternatives_filtered_by_max_price():
    def fake_search(product, max_price):
        return [
            {"name": "cheap", "price": 30.0, "why": ""},
            {"name": "too pricey", "price": max_price + 100, "why": ""},
        ]

    finder = AlternativeFinder(search_fn=fake_search)
    result = finder.find("widget", max_price=50.0)
    names = [r["name"] for r in result]
    assert "too pricey" not in names
    assert "cheap" in names


def test_format_alternatives_for_display():
    from src.task_engine.alternative_finder import format_alternatives

    out = format_alternatives("Sony WH-1000XM4", [
        {"name": "Anker Q45", "price": 79.99, "why": "great ANC"},
    ])
    assert "Sony WH-1000XM4" in out
    assert "Anker Q45" in out
    assert "$79.99" in out
