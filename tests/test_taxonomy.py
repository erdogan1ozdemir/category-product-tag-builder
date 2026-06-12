from facets.taxonomy import build_taxonomy_task, propose_taxonomy
from llm.bridge import MockBridge


def test_task_prompt_contains_sector_and_groups():
    t = build_taxonomy_task("kozmetik", ["Renk", "Hacim", "Kampanya"])
    assert "kozmetik" in t["prompt"]
    assert "Kampanya" in t["prompt"]
    assert t["schema"] == {"groups": "list"}


def test_propose_taxonomy_returns_group_names():
    b = MockBridge({"taxonomy_proposal": {"groups": [
        {"group": "Bitiş", "description": "mat/parlak"},
        {"group": "Cilt Tipi", "description": ""},
    ]}})
    out = propose_taxonomy("kozmetik", ["Renk"], b)
    assert [g["group"] for g in out["groups"]] == ["Bitiş", "Cilt Tipi"]
