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

    # Phase 1: build deterministic tags + LLM tasks for ALL categories
    all_tasks = []
    task_to_chunk_ids = {}  # task_id -> [product ids in that chunk]
    all_det = {}            # product_id -> det tags
    cat_for_product = {}    # product_id -> category
    pool_for_cat = {}       # category -> pool (only cats with a pool)
    no_pool_cats = set()

    for cat, products in by_cat.items():
        pool = pools_by_category.get(cat)
        if pool is None:
            for p in products:
                ws.append_jsonl("errors.jsonl", {"stage": "tag", "id": p["id"],
                                                 "error": f"havuz yok: {cat}"})
            no_pool_cats.add(cat)
            continue
        pool_for_cat[cat] = pool
        det = {p["id"]: deterministic_tags(p, pool) for p in products}
        all_det.update(det)
        for p in products:
            cat_for_product[p["id"]] = cat
        all_groups = set(pool_values(pool))
        need_llm = []
        for p in products:
            missing = sorted(all_groups - set(det[p["id"]]))
            if missing:
                need_llm.append({"id": p["id"], "name": p.get("name"),
                                 "description": (p.get("description") or "")[:500],
                                 "attributes": p.get("attributes") or {}, "missing": missing})
        for chunk in _chunks(need_llm, batch_size):
            task = build_tagging_task(cat, pool, chunk)
            all_tasks.append(task)
            task_to_chunk_ids[task["id"]] = [item["id"] for item in chunk]

    # Phase 2: single run_validated over all tasks
    llm_tags = {}
    failed_ids = set()
    if all_tasks:
        ok, failed = run_validated(bridge, all_tasks)
        for result in ok.values():
            for row in result.get("products", []):
                if isinstance(row, dict):
                    llm_tags[row.get("id")] = row.get("tags") or {}
        for task, errors in failed:
            ws.append_jsonl("errors.jsonl", {"stage": "tag", "task_id": task["id"],
                                             "error": "; ".join(errors)})
            for pid in task_to_chunk_ids.get(task["id"], []):
                failed_ids.add(pid)

    # Phase 3: write results, skipping products from failed chunks
    for cat, products in by_cat.items():
        if cat in no_pool_cats:
            continue
        pool = pool_for_cat[cat]
        valid = {g: {tr_lower(v): v for v in vals} for g, vals in pool_values(pool).items()}
        for p in products:
            if p["id"] in failed_ids:
                continue  # Stay pending; next run will retry
            tags = {g: {"value": v, "source": "deterministik"} for g, v in all_det[p["id"]].items()}
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
