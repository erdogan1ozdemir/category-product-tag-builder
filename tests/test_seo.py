from unittest.mock import patch, MagicMock
from facets.pool_builder import build_pool
from seo.cross_join import generate_combos
from seo.volume import apply_threshold, export_manual_csv, import_volumes_csv, fetch_volumes_dataforseo


def _pool():
    return build_pool("Abiye", [{"Renk": ["Kırmızı"], "Yaka Tipi": ["V Yaka"], "Beden": ["S"]}], None)


def test_generate_combos_single_and_pairs_excluding_groups():
    combos = generate_combos("Abiye", _pool(), exclude_groups=["Beden"],
                             two_facet_pairs=[["Renk", "Yaka Tipi"]])
    keywords = [c["combo"] for c in combos]
    assert "Kırmızı Abiye" in keywords
    assert "V Yaka Abiye" in keywords
    assert "Kırmızı V Yaka Abiye" in keywords
    assert all("S " not in k and not k.startswith("S ") for k in keywords)


def test_apply_threshold_marks_decision():
    combos = [{"combo": "Kırmızı Abiye"}, {"combo": "Mor Abiye"}]
    out = apply_threshold(combos, {"Kırmızı Abiye": 500, "Mor Abiye": 10}, threshold=100)
    assert out[0]["decision"] == "kategori"
    assert out[1]["decision"] == "filtre"


def test_manual_csv_roundtrip(tmp_path):
    path = str(tmp_path / "v.csv")
    export_manual_csv([{"combo": "Kırmızı Abiye"}], path)
    content = open(path, encoding="utf-8").read()
    assert "Kırmızı Abiye" in content
    open(path, "w", encoding="utf-8").write("combo,volume\nKırmızı Abiye,250\n")
    assert import_volumes_csv(path) == {"Kırmızı Abiye": 250}


def test_dataforseo_parses_volumes():
    resp = MagicMock(status_code=200)
    resp.json.return_value = {"tasks": [{"result": [
        {"keyword": "kırmızı abiye", "search_volume": 5400}]}]}
    with patch("seo.volume.requests.post", return_value=resp):
        out = fetch_volumes_dataforseo(["kırmızı abiye"], "user", "pass")
    assert out == {"kırmızı abiye": 5400}
