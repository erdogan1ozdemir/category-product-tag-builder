from core.state import Workspace
from facets.pool_builder import build_pool
from llm.bridge import MockBridge
from tagger.product_tagger import deterministic_tags
from tagger.batch import tag_products


def _pool():
    return build_pool("Ruj", [{"Bitiş": ["Mat", "Parlak"], "Ton": ["Kiremit", "Nude"]}], None)


def test_deterministic_finds_values_in_text():
    p = {"name": "Flormar Mat Ruj Kiremit", "description": "", "attributes": {}}
    tags = deterministic_tags(p, _pool())
    assert tags == {"Bitiş": "Mat", "Ton": "Kiremit"}


def test_deterministic_no_guess_when_absent():
    p = {"name": "Flormar Ruj", "description": "", "attributes": {}}
    assert deterministic_tags(p, _pool()) == {}


def test_tag_products_merges_llm_fills_and_resumes(tmp_path):
    ws = Workspace("m", root=str(tmp_path)).ensure()
    ws.append_jsonl("products/products.jsonl",
                    {"id": "p1", "name": "Mat Ruj", "category": "Ruj", "description": "", "attributes": {}})
    bridge = MockBridge({"product_tagging": {"products": [{"id": "p1", "tags": {"Ton": "Nude"}}]}})
    n = tag_products(ws, {"Ruj": _pool()}, bridge, batch_size=10)
    assert n == 1
    row = ws.read_jsonl("tagged/tagged.jsonl")[0]
    assert row["tags"]["Bitiş"] == {"value": "Mat", "source": "deterministik"}
    assert row["tags"]["Ton"] == {"value": "Nude", "source": "llm"}
    assert tag_products(ws, {"Ruj": _pool()}, bridge) == 0


def test_llm_value_case_insensitive_canonicalized(tmp_path):
    ws = Workspace("m", root=str(tmp_path)).ensure()
    ws.append_jsonl("products/products.jsonl",
                    {"id": "p1", "name": "Ruj", "category": "Ruj", "description": "", "attributes": {}})
    bridge = MockBridge({"product_tagging": {"products": [{"id": "p1", "tags": {"Ton": "nude", "Bitiş": "MAT"}}]}})
    tag_products(ws, {"Ruj": _pool()}, bridge)
    row = ws.read_jsonl("tagged/tagged.jsonl")[0]
    assert row["tags"]["Ton"] == {"value": "Nude", "source": "llm"}
    assert row["tags"]["Bitiş"] == {"value": "Mat", "source": "llm"}


def test_rejected_llm_values_logged(tmp_path):
    ws = Workspace("m", root=str(tmp_path)).ensure()
    ws.append_jsonl("products/products.jsonl",
                    {"id": "p1", "name": "Ruj", "category": "Ruj", "description": "", "attributes": {}})
    bridge = MockBridge({"product_tagging": {"products": [{"id": "p1", "tags": {"Ton": "Havuzda Yok"}}]}})
    tag_products(ws, {"Ruj": _pool()}, bridge)
    errs = [e for e in ws.read_jsonl("errors.jsonl") if e.get("stage") == "tag-reject"]
    assert len(errs) == 1
    assert errs[0]["id"] == "p1" and errs[0]["group"] == "Ton" and errs[0]["value"] == "Havuzda Yok"
