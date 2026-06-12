"""Kategori × facet kombinasyon türetme (atomik kategori adayları)."""
from facets.pool_builder import pool_values


def generate_combos(category: str, pool: dict, exclude_groups=None, two_facet_pairs=None) -> list:
    havuz = pool_values(pool)
    exclude = set(exclude_groups or [])
    combos, seen = [], set()

    def _add(combo, parts):
        if combo not in seen:
            seen.add(combo)
            combos.append({"combo": combo, "parts": parts})

    for group, values in havuz.items():
        if group in exclude:
            continue
        for value in values:
            _add(f"{value} {category}", {group: value})
    for pair in (two_facet_pairs or []):
        g1, g2 = pair[0], pair[1]
        for v1 in havuz.get(g1, []):
            for v2 in havuz.get(g2, []):
                _add(f"{v1} {v2} {category}", {g1: v1, g2: v2})
    return combos
