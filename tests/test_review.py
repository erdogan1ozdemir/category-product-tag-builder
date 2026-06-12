from core.state import Workspace
from facets.pool_builder import build_pool
from review.html_report import export_html_report


def test_html_report_contains_groups_and_values(tmp_path):
    ws = Workspace("m", root=str(tmp_path)).ensure()
    ws.write_json("pools/Ruj.json", build_pool("Ruj", [{"Bitiş": ["Mat", "Parlak"]}], None))
    path = export_html_report("Flormar", ws)
    html = open(path, encoding="utf-8").read()
    assert "Flormar" in html and "Ruj" in html and "Mat" in html and "Bitiş" in html


def test_html_report_creates_exports_dir(tmp_path):
    ws = Workspace("m", root=str(tmp_path))
    path = export_html_report("X", ws)
    import os
    assert os.path.exists(path)
