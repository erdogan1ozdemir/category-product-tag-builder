from llm.tasks import new_task, validate_result, extract_json


def test_new_task_id_is_deterministic():
    t1 = new_task("pool_quality", "aynı prompt", schema={"remove": "dict"})
    t2 = new_task("pool_quality", "aynı prompt", schema={"remove": "dict"})
    t3 = new_task("pool_quality", "farklı prompt", schema={"remove": "dict"})
    assert t1["id"] == t2["id"]
    assert t1["id"] != t3["id"]


def test_validate_result_ok():
    t = new_task("taxonomy_proposal", "p", schema={"groups": "list"})
    assert validate_result(t, {"groups": [{"group": "Renk"}]}) == []


def test_validate_result_missing_and_wrong_type():
    t = new_task("x", "p", schema={"groups": "list", "note": "str"})
    errs = validate_result(t, {"groups": "liste değil"})
    assert any("groups" in e for e in errs)
    assert any("note" in e for e in errs)


def test_extract_json_handles_fences_and_text():
    assert extract_json('{"a": 1}') == {"a": 1}
    assert extract_json('Açıklama:\n```json\n{"a": 1}\n```\nbitti') == {"a": 1}
    assert extract_json("hiç json yok") is None
