from facets.pool_builder import build_pool, pool_groups


def test_build_pool_merges_normalizes_and_keeps_v5_format():
    sources = [
        {"Renk": ["kırmızı", "KIRMIZI"], "Kampanya": ["2 al 1 öde"]},
        {"Renk": ["Lacivert"], "Bitiş": ["Mat"]},
    ]
    pool = build_pool("Ruj", sources, allowed_groups=["Renk", "Bitiş"])
    havuz = pool["gap_analizi"]["birlesik_filtre_havuzu"]
    assert pool["arama_kelimesi"] == "Ruj"
    assert havuz["Renk"] == ["Kırmızı", "Lacivert"]
    assert havuz["Bitiş"] == ["Mat"]
    assert "Kampanya" not in havuz


def test_build_pool_without_allowed_groups_keeps_all():
    pool = build_pool("Ruj", [{"Renk": ["Siyah"], "Doku": ["Krem"]}], allowed_groups=None)
    assert set(pool_groups(pool)) == {"Renk", "Doku"}


def test_empty_groups_dropped():
    pool = build_pool("Ruj", [{"Renk": ["  "]}], allowed_groups=None)
    assert pool_groups(pool) == []
