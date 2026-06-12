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
    resp.json.return_value = {"tasks": [{"status_code": 20000, "result": [
        {"keyword": "kırmızı abiye", "search_volume": 5400}]}]}
    with patch("seo.volume.requests.post", return_value=resp):
        out = fetch_volumes_dataforseo(["kırmızı abiye"], "user", "pass")
    assert out == {"kırmızı abiye": 5400}


def test_apply_threshold_matches_case_insensitive_turkish():
    combos = [{"combo": "Kırmızı Abiye"}]
    out = apply_threshold(combos, {"kırmızı abiye": 500}, threshold=100)
    assert out[0]["volume"] == 500 and out[0]["decision"] == "kategori"


def test_dataforseo_task_error_raises():
    import pytest
    resp = MagicMock(status_code=200)
    resp.json.return_value = {"tasks": [{"status_code": 40501, "status_message": "Invalid Field", "result": None}]}
    with patch("seo.volume.requests.post", return_value=resp):
        with pytest.raises(RuntimeError, match="40501"):
            fetch_volumes_dataforseo(["x"], "u", "p")


def test_dataforseo_chunks_over_1000_keywords():
    calls = []
    def fake_post(url, auth=None, json=None, timeout=None):
        calls.append(len(json[0]["keywords"]))
        resp = MagicMock(status_code=200)
        resp.json.return_value = {"tasks": [{"status_code": 20000, "result": []}]}
        return resp
    with patch("seo.volume.requests.post", side_effect=fake_post):
        fetch_volumes_dataforseo([f"kw {i}" for i in range(1500)], "u", "p")
    assert calls == [1000, 500]
