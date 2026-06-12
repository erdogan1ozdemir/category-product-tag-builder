import pytest
from core.pipeline import run_stage, STAGES
from core.brand_profile import BrandProfile
from core.state import Workspace
from llm.bridge import MockBridge, PendingLLMWork


def _brand():
    return BrandProfile(name="Marka", slug="m", sector="kozmetik")


def test_stages_order():
    assert STAGES == ["collect", "taxonomy", "pools", "review", "tag", "cross", "export"]


def test_unknown_stage_raises():
    with pytest.raises(ValueError, match="bilinmeyen aşama"):
        run_stage("yok", _brand(), {}, root="/tmp")


def test_pools_stage_builds_from_raw_sources(tmp_path):
    ws = Workspace("m", root=str(tmp_path)).ensure()
    ws.write_json("products/raw_facets.json", {"Ruj": [{"Bitiş": ["mat", "MAT"]}]})
    ws.write_json("pools/_taxonomy.json", {"groups": [{"group": "Bitiş"}]})
    bridge = MockBridge({"pool_quality": {"remove": {}, "merge": {}}})
    out = run_stage("pools", _brand(), {}, root=str(tmp_path), bridge=bridge)
    assert "Ruj" in out["built"]
    assert out["onay_dustu"] == []
    pool = ws.read_json("pools/Ruj.json")
    assert pool["gap_analizi"]["birlesik_filtre_havuzu"]["Bitiş"] == ["Mat"]


def test_cross_stage_writes_combos(tmp_path):
    ws = Workspace("m", root=str(tmp_path)).ensure()
    from facets.pool_builder import build_pool
    pool = build_pool("Ruj", [{"Bitiş": ["Mat"]}], None)
    pool["reviewed"] = True
    ws.write_json("pools/Ruj.json", pool)
    out = run_stage("cross", _brand(), {"seo": {"volume_threshold": 100}}, root=str(tmp_path))
    assert out["combos"] == 1
    combos = ws.read_json("combos/combos.json")
    assert combos[0]["combo"] == "Mat Ruj"
    assert combos[0]["decision"] == "filtre"


def test_cross_stage_skips_unreviewed_pools(tmp_path):
    ws = Workspace("m", root=str(tmp_path)).ensure()
    from facets.pool_builder import build_pool
    ws.write_json("pools/Ruj.json", build_pool("Ruj", [{"Bitiş": ["Mat"]}], None))
    out = run_stage("cross", _brand(), {"seo": {}}, root=str(tmp_path))
    assert out == {"combos": 0, "volume_source": "yok", "template_path": None}
    import os
    assert not os.path.exists(ws.path("input/volumes.csv"))


def test_cross_stage_stale_csv_regenerates_template(tmp_path):
    ws = Workspace("m", root=str(tmp_path)).ensure()
    from facets.pool_builder import build_pool
    pool = build_pool("Ruj", [{"Bitiş": ["Mat"]}], None)
    pool["reviewed"] = True
    ws.write_json("pools/Ruj.json", pool)
    import os
    os.makedirs(ws.path("input"), exist_ok=True)
    open(ws.path("input/volumes.csv"), "w", encoding="utf-8").write("combo,volume\nEski Combo,5\n")
    out = run_stage("cross", _brand(), {"seo": {}}, root=str(tmp_path))
    assert out["volume_source"] == "template"
    content = open(ws.path("input/volumes.csv"), encoding="utf-8").read()
    assert "Mat Ruj" in content


def test_pools_stage_sanitizes_category_names(tmp_path):
    ws = Workspace("m", root=str(tmp_path)).ensure()
    ws.write_json("products/raw_facets.json", {"Ruj/Set": [{"Bitiş": ["Mat"]}]})
    bridge = MockBridge({"pool_quality": {"remove": {}, "merge": {}}})
    run_stage("pools", _brand(), {}, root=str(tmp_path), bridge=bridge)
    import os
    assert os.path.exists(ws.path("pools/Ruj-Set.json"))


def test_pools_stage_reports_onay_dustu(tmp_path):
    ws = Workspace("m", root=str(tmp_path)).ensure()
    ws.write_json("products/raw_facets.json", {"Ruj": [{"Bitiş": ["Mat"]}]})
    bridge = MockBridge({"pool_quality": {"remove": {}, "merge": {}}})
    # First build — no previous pool
    out1 = run_stage("pools", _brand(), {}, root=str(tmp_path), bridge=bridge)
    assert out1["onay_dustu"] == []
    # Mark the pool as reviewed
    pool = ws.read_json("pools/Ruj.json")
    pool["reviewed"] = True
    ws.write_json("pools/Ruj.json", pool)
    # Rebuild — should detect that reviewed=True pool is being overwritten
    out2 = run_stage("pools", _brand(), {}, root=str(tmp_path), bridge=bridge)
    assert "Ruj" in out2["onay_dustu"]


def test_export_stage_writes_json_and_excel(tmp_path):
    ws = Workspace("m", root=str(tmp_path)).ensure()
    ws.append_jsonl("tagged/tagged.jsonl", {"id": "p1", "url": "u", "name": "X",
                                            "category": "Ruj", "tags": {}})
    out = run_stage("export", _brand(), {}, root=str(tmp_path), targets=["excel"])
    import os
    assert os.path.exists(out["json"]) and os.path.exists(out["excel"])


def test_collect_stage_parses_url_categories(tmp_path, monkeypatch):
    ws = Workspace("m", root=str(tmp_path)).ensure()
    import os
    os.makedirs(ws.path("input"), exist_ok=True)
    open(ws.path("input/urls.txt"), "w", encoding="utf-8").write(
        "# yorum\nhttps://x/1 Ruj Kalemi\nhttps://x/2\n")
    captured = {}
    def fake_collect(urls, ws_, delay=1.0, timeout=20, render_fallback=True, categories=None):
        captured["urls"] = urls
        captured["categories"] = categories
        return {"yeni": 0, "atlandı": 0, "hata": 0, "render": 0}
    import core.pipeline as cp
    monkeypatch.setattr("sources.generic_scraper.collect_from_urls", fake_collect)
    run_stage("collect", _brand(), {}, root=str(tmp_path))
    assert captured["urls"] == ["https://x/1", "https://x/2"]
    assert captured["categories"] == {"https://x/1": "Ruj Kalemi"}


def test_collect_stage_trendyol_url_categories(tmp_path, monkeypatch):
    ws = Workspace("m", root=str(tmp_path)).ensure()
    monkeypatch.setattr("sources.trendyol.fetch_aggregations",
                        lambda url, timeout=20: {"Renk": ["Kırmızı"]})
    monkeypatch.setattr("sources.trendyol.extract_category_seo_landings",
                        lambda url, cat: [])
    brand = BrandProfile(name="Marka", slug="m", sector="moda",
                         trendyol_urls=[{"url": "https://t/abiye-x-c56", "category": "Abiye"}])
    run_stage("collect", brand, {}, root=str(tmp_path))
    raw = ws.read_json("products/raw_facets.json")
    assert "Abiye" in raw


def test_pools_stage_single_pending_round_for_multiple_categories(tmp_path):
    ws = Workspace("m", root=str(tmp_path)).ensure()
    ws.write_json("products/raw_facets.json",
                  {"Ruj": [{"Bitiş": ["Mat"]}], "Maskara": [{"Etki": ["Hacim"]}]})
    from llm.inline_skill import InlineSkillBridge
    bridge = InlineSkillBridge(ws)
    with pytest.raises(PendingLLMWork) as exc:
        run_stage("pools", _brand(), {}, root=str(tmp_path), bridge=bridge)
    assert len(exc.value.files) == 2


def test_collect_stage_writes_seo_landings(tmp_path, monkeypatch):
    ws = Workspace("m", root=str(tmp_path)).ensure()
    monkeypatch.setattr("sources.trendyol.fetch_aggregations",
                        lambda url, timeout=20: {"Renk": ["Kırmızı"]})
    monkeypatch.setattr("sources.trendyol.extract_category_seo_landings",
                        lambda url, cat: [{"url": "/kirmizi-abiye-y-s1", "label": "Kırmızı Abiye"}])
    brand = BrandProfile(name="Marka", slug="m", sector="moda",
                         trendyol_urls=[{"url": "https://t/abiye-x-c56", "category": "Abiye"}])
    run_stage("collect", brand, {}, root=str(tmp_path))
    landings = ws.read_json("products/seo_landings.json")
    assert landings["Abiye"][0]["label"] == "Kırmızı Abiye"
