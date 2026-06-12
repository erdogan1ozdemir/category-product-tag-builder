import pytest
from core.pipeline import run_stage, STAGES
from core.brand_profile import BrandProfile
from core.state import Workspace
from llm.bridge import MockBridge


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
    run_stage("pools", _brand(), {}, root=str(tmp_path), bridge=bridge)
    pool = ws.read_json("pools/Ruj.json")
    assert pool["gap_analizi"]["birlesik_filtre_havuzu"]["Bitiş"] == ["Mat"]


def test_cross_stage_writes_combos(tmp_path):
    ws = Workspace("m", root=str(tmp_path)).ensure()
    from facets.pool_builder import build_pool
    pool = build_pool("Ruj", [{"Bitiş": ["Mat"]}], None)
    pool["reviewed"] = True
    ws.write_json("pools/Ruj.json", pool)
    run_stage("cross", _brand(), {"seo": {"volume_threshold": 100}}, root=str(tmp_path))
    combos = ws.read_json("combos/combos.json")
    assert combos[0]["combo"] == "Mat Ruj"
    assert combos[0]["decision"] == "filtre"


def test_cross_stage_skips_unreviewed_pools(tmp_path):
    ws = Workspace("m", root=str(tmp_path)).ensure()
    from facets.pool_builder import build_pool
    ws.write_json("pools/Ruj.json", build_pool("Ruj", [{"Bitiş": ["Mat"]}], None))
    run_stage("cross", _brand(), {"seo": {}}, root=str(tmp_path))
    assert ws.read_json("combos/combos.json") == []


def test_export_stage_writes_json_and_excel(tmp_path):
    ws = Workspace("m", root=str(tmp_path)).ensure()
    ws.append_jsonl("tagged/tagged.jsonl", {"id": "p1", "url": "u", "name": "X",
                                            "category": "Ruj", "tags": {}})
    out = run_stage("export", _brand(), {}, root=str(tmp_path), targets=["excel"])
    import os
    assert os.path.exists(out["json"]) and os.path.exists(out["excel"])
