import os
from sources.generic_scraper import parse_jsonld, parse_opengraph, parse_heuristic, scrape_product, collect_from_urls

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


def test_jsonld_string_offers_does_not_crash():
    html = ('<script type="application/ld+json">'
            '{"@type":"Product","name":"X","offers":"https://example.com/offer"}'
            '</script>')
    d = parse_jsonld(html)
    assert d["name"] == "X"
    assert d["price"] is None


def test_jsonld_list_brand_coerced_to_string():
    html = ('<script type="application/ld+json">'
            '{"@type":"Product","name":"X","brand":["MarkaY"]}'
            '</script>')
    assert parse_jsonld(html)["brand"] == "MarkaY"


def test_heuristic_decodes_html_entities():
    html = "<html><body><h1>Kad&#305;n Ti&#351;&#246;rt &amp; Atlet</h1></body></html>"
    assert parse_heuristic(html)["name"] == "Kadın Tişört & Atlet"


def test_scrape_product_survives_broken_layer():
    html = ('<html><head><meta property="og:title" content="Yedek Ad" /></head>'
            '<body><script type="application/ld+json">'
            '{"@type":"Product","offers":{"price":'
            '</script></body></html>')
    rec = scrape_product("https://example.com/p/2", html=html)
    assert rec["name"] == "Yedek Ad"


def test_collect_from_urls_skips_done_and_logs_errors(tmp_path, monkeypatch):
    from core.state import Workspace
    from sources import generic_scraper as gs
    ws = Workspace("m", root=str(tmp_path)).ensure()

    def fake_scrape(url, timeout=20):
        if "bozuk" in url:
            raise ValueError("ürün adı ayıklanamadı")
        from sources.base import product_record
        return product_record(url, name="Ürün")

    monkeypatch.setattr(gs, "scrape_product", fake_scrape)
    urls = ["https://x/1", "https://x/bozuk"]
    counts = gs.collect_from_urls(urls, ws, delay=0)
    assert counts == {"yeni": 1, "atlandı": 0, "hata": 1}
    counts2 = gs.collect_from_urls(urls, ws, delay=0)
    assert counts2["atlandı"] == 1
    errs = ws.read_jsonl("errors.jsonl")
    assert errs[0]["stage"] == "collect" and "bozuk" in errs[0]["url"]
