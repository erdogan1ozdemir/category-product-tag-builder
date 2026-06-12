import json
import subprocess
import sys


def _run(*args):
    return subprocess.run([sys.executable, "run.py", *args], capture_output=True, text=True,
                          cwd="/Users/Erdo/Desktop/Claude Projects/Özdilek/category-product-tag-builder")


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
