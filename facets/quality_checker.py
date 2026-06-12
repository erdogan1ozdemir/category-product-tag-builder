"""Havuz kalite denetimi: LLM'den remove/merge önerisi alır, deterministik uygular."""
import json

from llm.bridge import run_validated
from llm.tasks import new_task

from .normalizer import tr_lower
from .pool_builder import pool_values

PROMPT = """Sen bir e-ticaret veri kalitesi uzmanısın. Aşağıda '{category}' kategorisinin
facet havuzu var. Görevlerin:
1. Anlamsız/çöp değerleri tespit et (ürün kodu, rastgele sayı, pazarlama metni).
2. Aynı anlama gelen değerleri birleştir (yazım hatası, eşanlamlı) — doğru yazımı hedef yap.
Havuz: {pool_json}
JSON formatı: {{"remove": {{"Grup": ["değer"]}}, "merge": {{"Grup": {{"yanlış": "doğru"}}}}}}
Yalnızca havuzda gerçekten geçen grup ve değerleri kullan."""


def build_quality_task(category: str, pool: dict) -> dict:
    prompt = PROMPT.format(category=category,
                           pool_json=json.dumps(pool_values(pool), ensure_ascii=False))
    return new_task("pool_quality", prompt, schema={"remove": "dict", "merge": "dict"})


def apply_quality(pool: dict, result: dict) -> dict:
    havuz = {g: list(v) for g, v in pool_values(pool).items()}
    for group, values in (result.get("remove") or {}).items():
        if group in havuz:
            drop = {tr_lower(v) for v in values}
            havuz[group] = [v for v in havuz[group] if tr_lower(v) not in drop]
    for group, mapping in (result.get("merge") or {}).items():
        if group not in havuz:
            continue
        repl = {tr_lower(k): v for k, v in mapping.items()}
        seen, out = set(), []
        for v in havuz[group]:
            v = repl.get(tr_lower(v), v)
            if tr_lower(v) not in seen:
                seen.add(tr_lower(v))
                out.append(v)
        havuz[group] = out
    havuz = {g: v for g, v in havuz.items() if v}
    return {**pool, "gap_analizi": {**pool["gap_analizi"], "birlesik_filtre_havuzu": havuz}}


def check_pool(category: str, pool: dict, bridge) -> dict:
    task = build_quality_task(category, pool)
    ok, failed = run_validated(bridge, [task])
    if failed:
        raise RuntimeError(f"Kalite denetimi doğrulanamadı: {failed[0][1]}")
    return apply_quality(pool, ok[task["id"]])
