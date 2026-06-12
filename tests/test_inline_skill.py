import json
import pytest
from core.state import Workspace
from llm.inline_skill import InlineSkillBridge
from llm.bridge import PendingLLMWork
from llm.tasks import new_task


def test_writes_pending_file_and_raises(tmp_path):
    ws = Workspace("m", root=str(tmp_path)).ensure()
    b = InlineSkillBridge(ws)
    t = new_task("pool_quality", "havuzu temizle", schema={"remove": "dict"})
    with pytest.raises(PendingLLMWork) as exc:
        b.run_batch([t])
    pending = tmp_path / "m" / "pending_llm" / f"{t['id']}.json"
    assert pending.exists()
    written = json.loads(pending.read_text(encoding="utf-8"))
    assert written["prompt"] == "havuzu temizle"
    assert str(pending) in exc.value.files[0]


def test_reads_result_when_present(tmp_path):
    ws = Workspace("m", root=str(tmp_path)).ensure()
    b = InlineSkillBridge(ws)
    t = new_task("pool_quality", "havuzu temizle", schema={"remove": "dict"})
    result_path = tmp_path / "m" / "pending_llm" / f"{t['id']}.result.json"
    result_path.write_text(json.dumps({"remove": {"Renk": ["Junk"]}}), encoding="utf-8")
    out = b.run_batch([t])
    assert out[t["id"]]["remove"] == {"Renk": ["Junk"]}


def test_malformed_result_renamed_and_repending(tmp_path):
    ws = Workspace("m", root=str(tmp_path)).ensure()
    b = InlineSkillBridge(ws)
    t = new_task("pool_quality", "havuzu temizle", schema={"remove": "dict"})
    bad = tmp_path / "m" / "pending_llm" / f"{t['id']}.result.json"
    bad.write_text('{"remove": bozuk', encoding="utf-8")
    with pytest.raises(PendingLLMWork):
        b.run_batch([t])
    assert not bad.exists()
    assert (tmp_path / "m" / "pending_llm" / f"{t['id']}.result.invalid.json").exists()
    assert (tmp_path / "m" / "pending_llm" / f"{t['id']}.json").exists()
