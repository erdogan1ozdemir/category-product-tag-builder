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
