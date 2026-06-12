import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _run(*args):
    return subprocess.run([sys.executable, "run.py", *args], capture_output=True, text=True,
                          cwd=str(REPO_ROOT))


def test_help_lists_stages():
    out = _run("--help")
    assert out.returncode == 0
    for cmd in ("init", "collect", "pools", "tag", "cross", "export", "continue"):
        assert cmd in out.stdout


def test_stage_without_brand_fails_clearly():
    out = _run("collect")
    assert out.returncode != 0


def test_unknown_brand_fails_with_init_hint():
    out = _run("collect", "--brand", "boyle-bir-marka-yok")
    assert out.returncode != 0
    assert "init" in (out.stdout + out.stderr)


def test_pending_llm_exits_3_and_lists_files(tmp_path):
    import os
    import shutil

    slug = "cli-exit3-test"
    brand_path = REPO_ROOT / "brands" / f"{slug}.json"
    ws_path = REPO_ROOT / "workspace" / slug
    try:
        brand_path.write_text(
            json.dumps({"name": "T", "slug": slug, "sector": "moda"}),
            encoding="utf-8",
        )
        os.makedirs(ws_path / "products", exist_ok=True)
        (ws_path / "products" / "raw_facets.json").write_text(
            json.dumps({"Ruj": [{"Bitiş": ["Mat"]}]}), encoding="utf-8"
        )
        out = _run("taxonomy", "--brand", slug)
        assert out.returncode == 3
        assert "pending_llm" in out.stdout
    finally:
        brand_path.unlink(missing_ok=True)
        shutil.rmtree(ws_path, ignore_errors=True)
