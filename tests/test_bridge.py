import pytest
from llm.bridge import MockBridge, LLMError, get_bridge, run_validated
from llm.tasks import new_task


def test_mock_bridge_returns_canned_response():
    b = MockBridge({"pool_quality": {"remove": {}, "merge": {}}})
    t = new_task("pool_quality", "p", schema={"remove": "dict", "merge": "dict"})
    assert b.run_batch([t]) == {t["id"]: {"remove": {}, "merge": {}}}


def test_get_bridge_unknown_provider_raises():
    with pytest.raises(LLMError, match="bilinmeyen"):
        get_bridge({"llm": {"provider": "yok-böyle-bir-şey"}})


def test_run_validated_separates_ok_and_failed():
    b = MockBridge({"iyi": {"groups": []}, "kötü": {"yanlış": 1}})
    t_ok = new_task("iyi", "p1", schema={"groups": "list"})
    t_bad = new_task("kötü", "p2", schema={"groups": "list"})
    ok, failed = run_validated(b, [t_ok, t_bad], max_retries=0)
    assert t_ok["id"] in ok
    assert len(failed) == 1 and failed[0][0]["id"] == t_bad["id"]
