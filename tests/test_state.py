from core.state import Workspace


def test_ensure_creates_subdirs(tmp_path):
    ws = Workspace("flormar", root=str(tmp_path))
    ws.ensure()
    for d in ("input", "products", "pools", "pending_llm", "tagged", "combos", "exports"):
        assert (tmp_path / "flormar" / d).is_dir()


def test_jsonl_roundtrip_and_processed_ids(tmp_path):
    ws = Workspace("m", root=str(tmp_path))
    ws.ensure()
    ws.append_jsonl("products/products.jsonl", {"id": "a1", "name": "Ruj"})
    ws.append_jsonl("products/products.jsonl", {"id": "b2", "name": "Maskara"})
    rows = ws.read_jsonl("products/products.jsonl")
    assert [r["id"] for r in rows] == ["a1", "b2"]
    assert ws.processed_ids("products/products.jsonl") == {"a1", "b2"}


def test_read_jsonl_missing_returns_empty(tmp_path):
    ws = Workspace("m", root=str(tmp_path))
    assert ws.read_jsonl("yok.jsonl") == []


def test_json_roundtrip_atomic(tmp_path):
    ws = Workspace("m", root=str(tmp_path))
    ws.ensure()
    ws.write_json("pools/Ruj.json", {"arama_kelimesi": "Ruj"})
    assert ws.read_json("pools/Ruj.json")["arama_kelimesi"] == "Ruj"
    assert ws.read_json("yok.json", default={}) == {}


def test_read_jsonl_tolerates_corrupt_final_line(tmp_path):
    ws = Workspace("m", root=str(tmp_path))
    ws.ensure()
    ws.append_jsonl("products/products.jsonl", {"id": "a1"})
    with open(ws.path("products/products.jsonl"), "a", encoding="utf-8") as f:
        f.write('{"id": "b2", "na')
    rows = ws.read_jsonl("products/products.jsonl")
    assert [r["id"] for r in rows] == ["a1"]


def test_read_jsonl_corrupt_middle_line_raises_with_location(tmp_path):
    import pytest
    ws = Workspace("m", root=str(tmp_path))
    ws.ensure()
    with open(ws.path("x.jsonl"), "w", encoding="utf-8") as f:
        f.write('bozuk\n{"id": "a1"}\n')
    with pytest.raises(ValueError, match="x.jsonl.*1"):
        ws.read_jsonl("x.jsonl")
