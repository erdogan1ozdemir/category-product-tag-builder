import os
from sources.generic_scraper import parse_jsonld, parse_opengraph, parse_heuristic, scrape_product

FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def _read(name):
    with open(os.path.join(FIX, name), encoding="utf-8") as f:
        return f.read()


def test_jsonld_product():
    d = parse_jsonld(_read("jsonld_product.html"))
    assert d["name"] == "Mat Ruj 03 Kiremit"
    assert d["brand"] == "Flormar"
    assert d["attributes"] == {"Bitiş": "Mat", "Ton": "Kiremit"}
    assert d["price"] == "199.90"


def test_opengraph_fallback():
    d = parse_opengraph(_read("og_product.html"))
    assert d["name"] == "Seramik Lavabo 60 cm"
    assert d["images"] == ["https://cdn.example.com/lavabo.jpg"]


def test_heuristic_table_attributes():
    d = parse_heuristic(_read("plain_product.html"))
    assert d["name"] == "Pamuklu Tişört"
    assert d["attributes"] == {"Materyal": "Pamuk", "Renk": "Lacivert"}


def test_scrape_product_merges_with_priority():
    rec = scrape_product("https://example.com/p/1", html=_read("jsonld_product.html"))
    assert rec["name"] == "Mat Ruj 03 Kiremit"
    assert rec["url"] == "https://example.com/p/1"
    assert len(rec["id"]) == 12
