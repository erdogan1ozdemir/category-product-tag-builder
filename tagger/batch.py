"""Toplu etiketleme: resume destekli, hatalar errors.jsonl'a düşer."""
from facets.normalizer import tr_lower
from facets.pool_builder import pool_values
from llm.bridge import run_validated

from .product_tagger import build_tagging_task, deterministic_tags


def _chunks(seq, size):
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


def tag_products(ws, pools_by_category: dict, bridge, batch_size: int = 50) -> int:
    done = ws.processed_ids("tagged/tagged.jsonl")
    pending = [p for p in ws.read_jsonl("products/products.jsonl") if p["id"] not in done]
    written = 0
    by_cat = {}
    for p in pending:
        cat = p.get("category") or "Genel"
        by_cat.setdefault(cat, []).append(p)
    for cat, products in by_cat.items():
        pool = pools_by_category.get(cat)
        if pool is None:
            for p in products:
                ws.append_jsonl("errors.jsonl", {"stage": "tag", "id": p["id"],
                                                 "error": f"havuz yok: {cat}"})
            continue
        det = {p["id"]: deterministic_tags(p, pool) for p in products}
        all_groups = set(pool_values(pool))
        need_llm = []
        for p in products:
            missing = sorted(all_groups - set(det[p["id"]]))
            if missing:
                need_llm.append({"id": p["id"], "name": p.get("name"),
                                 "description": (p.get("description") or "")[:500],
                                 "attributes": p.get("attributes") or {}, "missing": missing})
        llm_tags = {}
        if need_llm:
            tasks = [build_tagging_task(cat, pool, chunk) for chunk in _chunks(need_llm, batch_size)]
            ok, failed = run_validated(bridge, tasks)
            for result in ok.values():
                for row in result.get("products", []):
                    if isinstance(row, dict):
                        llm_tags[row.get("id")] = row.get("tags") or {}
            for task, errors in failed:
                ws.append_jsonl("errors.jsonl", {"stage": "tag", "task_id": task["id"],
                                                 "error": "; ".join(errors)})
        valid = {g: {tr_lower(v): v for v in vals} for g, vals in pool_values(pool).items()}
        for p in products:
            tags = {g: {"value": v, "source": "deterministik"} for g, v in det[p["id"]].items()}
            llm_t = llm_tags.get(p["id"], {})
            if isinstance(llm_t, dict):
                for g, v in llm_t.items():
                    if not isinstance(v, str):
                        continue
                    if g in valid:
                        canon = valid[g].get(tr_lower(v))
                        if canon is not None and g not in tags:
                            tags[g] = {"value": canon, "source": "llm"}
                        elif canon is None:
                            ws.append_jsonl("errors.jsonl",
                                            {"stage": "tag-reject", "id": p["id"], "group": g, "value": v})
            ws.append_jsonl("tagged/tagged.jsonl",
                            {"id": p["id"], "url": p.get("url"), "name": p.get("name"),
                             "category": cat, "tags": tags})
            written += 1
    return written
