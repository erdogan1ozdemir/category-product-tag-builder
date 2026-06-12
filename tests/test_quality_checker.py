from facets.quality_checker import apply_quality, check_pool
from facets.pool_builder import build_pool
from llm.bridge import MockBridge


def _pool():
    return build_pool("Ruj", [{"Renk": ["Kırmızı", "Kirmizi", "Junk123"], "Bitiş": ["Mat"]}], None)


def test_apply_quality_removes_and_merges():
    result = {"remove": {"Renk": ["Junk123"]}, "merge": {"Renk": {"Kirmizi": "Kırmızı"}}}
    cleaned = apply_quality(_pool(), result)
    assert cleaned["gap_analizi"]["birlesik_filtre_havuzu"]["Renk"] == ["Kırmızı"]
    assert cleaned["gap_analizi"]["birlesik_filtre_havuzu"]["Bitiş"] == ["Mat"]


def test_apply_quality_ignores_unknown_groups():
    cleaned = apply_quality(_pool(), {"remove": {"Yok": ["x"]}, "merge": {}})
    assert "Yok" not in cleaned["gap_analizi"]["birlesik_filtre_havuzu"]


def test_check_pool_via_bridge():
    b = MockBridge({"pool_quality": {"remove": {"Renk": ["Junk123"]}, "merge": {}}})
    cleaned = check_pool("Ruj", _pool(), b)
    assert "Junk123" not in cleaned["gap_analizi"]["birlesik_filtre_havuzu"]["Renk"]
