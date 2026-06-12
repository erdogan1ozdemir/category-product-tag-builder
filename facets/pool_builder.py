"""Kaynak facet verilerini birleştirip normalize ederek v5 formatında havuz üretir."""
from collections import defaultdict

from .normalizer import normalize_value_list, tr_lower


def build_pool(category: str, source_maps: list, allowed_groups=None) -> dict:
    merged = defaultdict(list)
    for source in source_maps:
        for group, values in (source or {}).items():
            merged[group].extend(values)
    if allowed_groups is not None:
        allowed = {tr_lower(g) for g in allowed_groups}
        merged = {g: v for g, v in merged.items() if tr_lower(g) in allowed}
    havuz = {}
    for group, values in merged.items():
        normalized = normalize_value_list(values, group_name=group)
        if normalized:
            havuz[group] = sorted(normalized, key=tr_lower)
    return {"arama_kelimesi": category, "gap_analizi": {"birlesik_filtre_havuzu": havuz}}


def pool_groups(pool: dict) -> list:
    return list(pool.get("gap_analizi", {}).get("birlesik_filtre_havuzu", {}).keys())


def pool_values(pool: dict) -> dict:
    return pool.get("gap_analizi", {}).get("birlesik_filtre_havuzu", {})
