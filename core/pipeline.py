"""Aşama orkestrasyonu. Her aşama bağımsız; inline modda PendingLLMWork üst katmana taşar."""
import os
import re

from .state import Workspace


def _safe_category(name: str) -> str:
    cleaned = re.sub(r"[\\/\x00-\x1f]", "-", str(name or "")).strip().lstrip("_").strip()
    return cleaned

STAGES = ["collect", "taxonomy", "pools", "review", "tag", "cross", "export"]


def _bridge(config, ws, override=None):
    if override is not None:
        return override
    from llm.bridge import get_bridge
    return get_bridge(config, workspace=ws)


def _iter_pools(ws, only_reviewed=False):
    pools_dir = ws.path("pools")
    if not os.path.isdir(pools_dir):
        return
    for name in sorted(os.listdir(pools_dir)):
        if name.endswith(".json") and not name.startswith("_"):
            pool = ws.read_json(f"pools/{name}")
            if only_reviewed and not pool.get("reviewed"):
                continue
            yield name[:-5], pool


def stage_collect(brand, config, ws, **opts):
    from sources import generic_scraper as gs_mod
    from sources import trendyol as ty_mod
    sc = config.get("scraper", {})
    url_file = ws.path("input/urls.txt")
    urls = []
    categories = {}
    if os.path.exists(url_file):
        with open(url_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split(None, 1)
                urls.append(parts[0])
                if len(parts) > 1:
                    categories[parts[0]] = parts[1].strip()
    counts = gs_mod.collect_from_urls(
        urls, ws,
        delay=sc.get("delay_seconds", 1.0),
        timeout=sc.get("timeout", 20),
        render_fallback=sc.get("playwright_fallback", True),
        categories=categories,
    ) if urls else {}
    raw = ws.read_json("products/raw_facets.json", default={})
    trendyol_bos = []
    seo_landings = {}
    for entry in brand.trendyol_urls:
        if isinstance(entry, dict):
            ty_url, ty_cat = entry.get("url"), entry.get("category")
        else:
            ty_url, ty_cat = entry, None
        if not ty_url:
            continue
        aggs = ty_mod.fetch_aggregations(ty_url)
        if aggs:
            key = ty_cat or opts.get("category") or brand.name
            raw.setdefault(key, []).append(aggs)
            try:
                landings = ty_mod.extract_category_seo_landings(ty_url, key)
                if landings:
                    seo_landings.setdefault(key, []).extend(landings)
            except Exception:
                pass
        else:
            trendyol_bos.append(ty_url)
    ws.write_json("products/raw_facets.json", raw)
    if seo_landings:
        ws.write_json("products/seo_landings.json", seo_landings)
    if trendyol_bos:
        ws.append_jsonl("errors.jsonl", {"stage": "collect-trendyol",
                                         "error": "boş aggregation (engel/yanlış URL olabilir)",
                                         "urls": trendyol_bos})
    return {**counts, "trendyol_bos": len(trendyol_bos)}


def stage_taxonomy(brand, config, ws, bridge=None, **opts):
    from facets.taxonomy import propose_taxonomy
    raw = ws.read_json("products/raw_facets.json", default={})
    raw_groups = sorted({g for maps in raw.values() for m in maps for g in m})
    for p in ws.read_jsonl("products/products.jsonl"):
        raw_groups.extend((p.get("attributes") or {}).keys())
    result = propose_taxonomy(brand.sector, sorted(set(raw_groups)),
                              _bridge(config, ws, bridge))
    ws.write_json("pools/_taxonomy.json", result)
    return result


def stage_pools(brand, config, ws, bridge=None, **opts):
    from facets.pool_builder import build_pool
    from facets.quality_checker import apply_quality, build_quality_task
    from llm.bridge import LLMError, run_validated
    taxonomy = ws.read_json("pools/_taxonomy.json", default=None)
    allowed = [g["group"] for g in taxonomy["groups"]] if taxonomy else None
    raw = ws.read_json("products/raw_facets.json", default={})
    by_category = {k: list(v) for k, v in raw.items()}
    for p in ws.read_jsonl("products/products.jsonl"):
        cat = p.get("category") or "Genel"
        attrs = {k: [v] for k, v in (p.get("attributes") or {}).items()}
        if attrs:
            by_category.setdefault(cat, []).append(attrs)
    b = _bridge(config, ws, bridge)

    # Phase 1: build ALL pools first (skip empty/invalid); collect quality tasks
    built_pools = {}      # safe_name -> pool (pre-quality)
    quality_tasks = []    # [{task, safe_name}]
    task_to_cat = {}      # task_id -> safe_name
    onay_dustu = []

    for category, source_maps in by_category.items():
        safe = _safe_category(category)
        if not safe:
            ws.append_jsonl("errors.jsonl", {"stage": "pools", "category": category,
                                             "error": "geçersiz kategori adı"})
            continue
        pool = build_pool(safe, source_maps, allowed_groups=allowed)
        if not pool["gap_analizi"]["birlesik_filtre_havuzu"]:
            ws.append_jsonl("errors.jsonl", {"stage": "pools", "category": category,
                                             "error": "boş havuz — kaynak veri yetersiz"})
            continue
        task = build_quality_task(safe, pool)
        built_pools[safe] = pool
        quality_tasks.append(task)
        task_to_cat[task["id"]] = safe

    # Phase 2: single run_validated for all quality tasks
    if not quality_tasks:
        return {"built": [], "onay_dustu": []}

    ok, failed = run_validated(b, quality_tasks)

    # Raise LLMError for API providers when tasks permanently fail
    # (with inline bridge, invalidate already re-queued them — PendingLLMWork covers it)
    if failed:
        msgs = "; ".join(
            f"{task_to_cat.get(t['id'], t['id'])}: {errs}"
            for t, errs in failed
        )
        raise LLMError(f"Kalite denetimi doğrulanamadı — {msgs}")

    # Phase 3: apply quality results and write pools
    built = []
    for task in quality_tasks:
        safe = task_to_cat[task["id"]]
        pool = apply_quality(built_pools[safe], ok[task["id"]])
        existing = ws.read_json(f"pools/{safe}.json", default=None)
        if existing is not None and existing.get("reviewed"):
            onay_dustu.append(safe)
        ws.write_json(f"pools/{safe}.json", pool)
        built.append(safe)

    return {"built": built, "onay_dustu": onay_dustu}


def stage_review(brand, config, ws, **opts):
    from review.html_report import export_html_report
    path = export_html_report(brand.name, ws)
    return {"html_report": path,
            "not": "Onay: sohbet içinde, streamlit run review/streamlit_app.py ile "
                   "veya HTML raporu paylaşarak. Onaylanan havuza reviewed=true yazılmalı."}


def stage_tag(brand, config, ws, bridge=None, **opts):
    from tagger.batch import tag_products
    pools = {cat: pool for cat, pool in _iter_pools(ws)}
    batch_size = config.get("llm", {}).get("batch_size", 50)
    return tag_products(ws, pools, _bridge(config, ws, bridge), batch_size=batch_size)


def stage_cross(brand, config, ws, **opts):
    from seo.cross_join import generate_combos
    from seo.volume import (apply_threshold, export_manual_csv,
                            fetch_volumes_dataforseo, import_volumes_csv)
    seo_cfg = config.get("seo", {})
    combos = []
    for category, pool in _iter_pools(ws, only_reviewed=True):
        combos.extend(generate_combos(category, pool,
                                      exclude_groups=seo_cfg.get("exclude_groups"),
                                      two_facet_pairs=seo_cfg.get("two_facet_pairs")))

    if not combos:
        ws.write_json("combos/combos.json", [])
        return {"combos": 0, "volume_source": "yok", "template_path": None}

    dfs = config.get("dataforseo", {})
    manual_csv = ws.path("input/volumes.csv")
    volume_source = "template"
    template_path = None

    if opts.get("import_volumes"):
        volumes = import_volumes_csv(opts["import_volumes"])
        volume_source = "import"
    elif dfs.get("login") and dfs.get("password"):
        volumes = fetch_volumes_dataforseo([c["combo"] for c in combos],
                                           dfs["login"], dfs["password"])
        volume_source = "dataforseo"
    elif os.path.exists(manual_csv):
        volumes = import_volumes_csv(manual_csv)
        current_combo_set = {c["combo"] for c in combos}
        if not any(k in current_combo_set for k in volumes):
            # Stale CSV — no overlap with current combos; regenerate template
            export_manual_csv(combos, manual_csv)
            volumes = {}
            volume_source = "template"
            template_path = manual_csv
        else:
            volume_source = "csv"
    else:
        export_manual_csv(combos, manual_csv)
        volumes = {}
        volume_source = "template"
        template_path = manual_csv

    ws.write_json("combos/combos.json",
                  apply_threshold(combos, volumes, seo_cfg.get("volume_threshold", 100)))
    return {"combos": len(combos), "volume_source": volume_source, "template_path": template_path}


def stage_export(brand, config, ws, **opts):
    from outputs.json_sink import export_json
    out = {"json": export_json(brand.slug, ws)}
    targets = opts.get("targets") or ["excel"]
    if "excel" in targets:
        from outputs.excel_sink import export_excel
        out["excel"] = export_excel(brand.slug, ws)
    if "supabase" in targets:
        sb = config.get("supabase", {})
        if sb.get("url") and sb.get("service_key"):
            from outputs.supabase_sink import export_supabase
            export_supabase(brand.slug, ws, sb)
            out["supabase"] = "yazıldı"
        else:
            out["supabase"] = "atlandı — config.json'da supabase.url/service_key boş"
    return out


_HANDLERS = {
    "collect": stage_collect, "taxonomy": stage_taxonomy, "pools": stage_pools,
    "review": stage_review, "tag": stage_tag, "cross": stage_cross, "export": stage_export,
}


def run_stage(stage: str, brand, config: dict, root: str = "workspace",
              bridge=None, **opts):
    if stage not in _HANDLERS:
        raise ValueError(f"bilinmeyen aşama: {stage} (geçerli: {', '.join(STAGES)})")
    ws = Workspace(brand.slug, root=root).ensure()
    ws.write_json("_stage.json", {"stage": stage})
    kwargs = dict(opts)
    if stage in ("taxonomy", "pools", "tag"):
        kwargs["bridge"] = bridge
    return _HANDLERS[stage](brand, config, ws, **kwargs)
