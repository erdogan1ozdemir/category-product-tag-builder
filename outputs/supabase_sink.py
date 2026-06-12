"""Supabase PostgREST sink: brand_slug ile çok kiracılı upsert. Şema: docs/supabase_schema.sql"""
import os

import requests


class SupabaseSink:
    def __init__(self, url: str, service_key: str):
        self.url = url.rstrip("/")
        self.key = service_key

    def upsert(self, table: str, rows: list, conflict: str):
        if not rows:
            return
        headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates",
        }
        for i in range(0, len(rows), 500):
            chunk = rows[i:i + 500]
            resp = requests.post(
                f"{self.url}/rest/v1/{table}",
                params={"on_conflict": conflict},
                headers=headers,
                json=chunk,
                timeout=60,
            )
            if resp.status_code not in (200, 201, 204):
                raise RuntimeError(f"Supabase {table} upsert hatası {resp.status_code}: {resp.text[:300]}")


def export_supabase(brand_slug: str, ws, cfg: dict):
    sink = SupabaseSink(cfg["url"], cfg["service_key"])
    pools_dir = ws.path("pools")
    pool_rows = []
    if os.path.isdir(pools_dir):
        for name in sorted(os.listdir(pools_dir)):
            if name.endswith(".json") and not name.startswith("_"):
                pool_rows.append({"brand_slug": brand_slug, "category": name[:-5],
                                  "pool": ws.read_json(f"pools/{name}")})
    sink.upsert("pools", pool_rows, conflict="brand_slug,category")
    tag_rows = [{"brand_slug": brand_slug, "product_id": r["id"], "url": r.get("url"),
                 "name": r.get("name"), "category": r.get("category"), "tags": r.get("tags")}
                for r in ws.read_jsonl("tagged/tagged.jsonl")]
    sink.upsert("product_tags", tag_rows, conflict="brand_slug,product_id")
    combo_rows = [{"brand_slug": brand_slug, "combo": c["combo"], "volume": c.get("volume"),
                   "decision": c.get("decision"), "parts": c.get("parts")}
                  for c in ws.read_json("combos/combos.json", default=[])]
    sink.upsert("combos", combo_rows, conflict="brand_slug,combo")
