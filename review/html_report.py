"""Salt-okunur statik HTML havuz raporu — GitHub Pages/Vercel'de paylaşılabilir."""
import html as html_mod
import os

from facets.pool_builder import pool_values

TEMPLATE = """<!DOCTYPE html><html lang="tr"><head><meta charset="utf-8">
<title>{brand} — Facet Havuz Raporu</title>
<style>body{{font-family:system-ui;margin:2rem;max-width:960px}}h2{{border-bottom:2px solid #eee;padding-bottom:4px}}
table{{border-collapse:collapse;width:100%;margin-bottom:1.5rem}}td,th{{border:1px solid #ddd;padding:6px 10px;text-align:left;vertical-align:top}}
th{{background:#f7f7f7}}.count{{color:#888;font-size:0.85em}}</style></head><body>
<h1>{brand} — Facet Havuz Raporu</h1>{sections}</body></html>"""


def export_html_report(brand_name: str, ws) -> str:
    sections = []
    pools_dir = ws.path("pools")
    if os.path.isdir(pools_dir):
        for name in sorted(os.listdir(pools_dir)):
            if not name.endswith(".json") or name.startswith("_"):
                continue
            pool = ws.read_json(f"pools/{name}")
            rows = "".join(
                f"<tr><th>{html_mod.escape(g)} <span class='count'>({len(v)})</span></th>"
                f"<td>{html_mod.escape(', '.join(v))}</td></tr>"
                for g, v in pool_values(pool).items()
            )
            sections.append(f"<h2>{html_mod.escape(name[:-5])}</h2><table>{rows}</table>")
    out = ws.path("exports/report.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(TEMPLATE.format(brand=html_mod.escape(brand_name), sections="".join(sections)))
    return out
