"""Kaynak facet verilerini birleştirip normalize ederek v5 formatında havuz üretir."""
from collections import defaultdict

from .normalizer import normalize_value_list, tr_lower


def build_pool(category: str, source_maps: list, allowed_groups=None) -> dict:
    merged = defaultdict(list)
    for source in source_maps:
        for group, values in (source or {}).items():
            merged[group].extend(values)
    if allowed_groups is not None:
        # Build a canonical map: tr_lower(name) -> canonical name from allowed_groups
        canon = {tr_lower(g): g for g in allowed_groups}
        canonical_buckets: dict = {}
        for g, v in merged.items():
            key = tr_lower(g)
            if key in canon:
                canonical_buckets.setdefault(canon[key], []).extend(v)
        merged = canonical_buckets
    else:
        # Merge case-variant duplicates into the first-seen casing
        canon_fly: dict = {}  # tr_lower(g) -> first-seen canonical name
        canonical_buckets2: dict = {}
        for g, v in merged.items():
            key = tr_lower(g)
            if key not in canon_fly:
                canon_fly[key] = g
            canonical_buckets2.setdefault(canon_fly[key], []).extend(v)
        merged = canonical_buckets2
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
