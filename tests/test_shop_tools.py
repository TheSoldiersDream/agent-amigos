import pytest
from backend.tools.shop_tools import _parse_price, search_products


def test_parse_price_dollar_and_php():
    assert _parse_price("AUD $549.00") == {"amount": 549.0, "currency": "AUD"}
    assert _parse_price("₱ 23,500") == {"amount": 23500.0, "currency": "PHP"}


def test_search_products_basic(monkeypatch):
    # Monkeypatch web_search and scrape_url to avoid network
    def fake_web_search(q, max_results=5):
        return {"results": [{"title": "Starlink Kit - Example Seller", "href": "https://example.com/item/1", "body": "Buy Starlink ₱ 23500"}]}

    def fake_scrape_url(url, **kwargs):
        return {"success": True, "text": "Starlink Satellite Kit ₱ 23500", "metadata": {"title": "Example Seller"}}

    monkeypatch.setattr('tools.web_tools.web_search', fake_web_search)
    monkeypatch.setattr('tools.scraper_tools.scrape_url', fake_scrape_url)

    res = search_products("starlink kit philippines", limit=2)
    assert res["query"].startswith("starlink")
    assert len(res["results"]) >= 1
    p = res["results"][0]
    assert p["price"]["currency"] == "PHP"
    assert "PHP" in p["price_converted"] or "AUD" in p["price_converted"]