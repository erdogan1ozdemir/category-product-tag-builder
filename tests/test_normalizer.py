from facets.normalizer import normalize_value_list, tr_lower, tr_title


def test_tr_lower_turkish_chars():
    assert tr_lower("İstanbul") == "istanbul"
    assert tr_lower("ISPARTA") == "ısparta"


def test_tr_title():
    assert tr_title("kırmızı çiçek") == "Kırmızı Çiçek"


def test_normalize_dedups_case_insensitive_and_strips():
    out = normalize_value_list(["kırmızı", "KIRMIZI", "Kırmızı ", "  ", "Lacivert"])
    assert out == ["Kırmızı", "Lacivert"]


def test_normalize_splits_composite_material():
    out = normalize_value_list(["%100 Pamuk", "Pamuk / Polyester"], group_name="Materyal")
    assert out == ["Pamuk", "Polyester"]
