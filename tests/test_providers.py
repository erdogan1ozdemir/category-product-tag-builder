import json
from unittest.mock import patch, MagicMock
from llm.claude_cli import ClaudeCLIBridge
from llm.api_clients import ApiBridge
from llm.tasks import new_task


def _fake_proc(stdout, returncode=0):
    m = MagicMock()
    m.stdout, m.returncode, m.stderr = stdout, returncode, ""
    return m


def test_claude_cli_parses_result_envelope():
    t = new_task("x", "soru", schema={"a": "int"})
    envelope = json.dumps({"result": '{"a": 1}'})
    with patch("llm.claude_cli.subprocess.run", return_value=_fake_proc(envelope)) as run:
        out = ClaudeCLIBridge(model="").run_batch([t])
    assert out[t["id"]] == {"a": 1}
    assert "claude" in run.call_args[0][0][0]


def test_api_bridge_anthropic():
    t = new_task("x", "soru", schema={"a": "int"})
    resp = MagicMock(status_code=200)
    resp.json.return_value = {"content": [{"text": '{"a": 2}'}]}
    with patch("llm.api_clients.requests.post", return_value=resp):
        out = ApiBridge("anthropic", {"anthropic_api_key": "k"}).run_batch([t])
    assert out[t["id"]] == {"a": 2}


def test_api_bridge_missing_key_raises():
    import pytest
    from llm.bridge import LLMError
    with pytest.raises(LLMError, match="anahtar"):
        ApiBridge("gemini", {})


def test_claude_cli_nonjson_stdout_raises_llmerror():
    import pytest
    from llm.bridge import LLMError
    t = new_task("x", "soru", schema={"a": "int"})
    with patch("llm.claude_cli.subprocess.run", return_value=_fake_proc("uyarı: bir şey oldu")):
        with pytest.raises(LLMError, match="JSON değil"):
            ClaudeCLIBridge(model="").run_batch([t])


def test_api_bridge_connection_error_raises_llmerror():
    import pytest
    import requests as req
    from llm.bridge import LLMError
    t = new_task("x", "soru", schema={"a": "int"})
    with patch("llm.api_clients.requests.post", side_effect=req.ConnectionError("boom")):
        with pytest.raises(LLMError, match="bağlantı"):
            ApiBridge("anthropic", {"anthropic_api_key": "k"}).run_batch([t])
