"""Konsolide JSON dışa aktarımı: havuzlar + etiket sayısı + kombinasyonlar tek dosyada."""
import json
import os


def export_json(brand_slug: str, ws) -> str:
    pools = {}
    pools_dir = ws.path("pools")
    if os.path.isdir(pools_dir):
        for name in sorted(os.listdir(pools_dir)):
            if name.endswith(".json") and not name.startswith("_"):
                pools[name[:-5]] = ws.read_json(f"pools/{name}")
    data = {
        "brand": brand_slug,
        "pools": pools,
        "tagged_count": len(ws.read_jsonl("tagged/tagged.jsonl")),
        "combos": ws.read_json("combos/combos.json", default=[]),
    }
    out = ws.path("exports/export.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return out
