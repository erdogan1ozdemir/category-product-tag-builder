"""LLMBridge: tek arayüz, provider fabrikası, doğrulamalı çalıştırma."""
from .tasks import validate_result


class LLMError(Exception):
    pass


class PendingLLMWork(Exception):
    """inline modda: sonuç bekleyen görev dosyaları var."""

    def __init__(self, files):
        self.files = files
        super().__init__(
            "LLM sonucu bekleyen görevler var:\n"
            + "\n".join(f"  - {f}" for f in files)
            + "\nHer görev dosyasını okuyup <id>.result.json yazın, sonra komutu tekrar çalıştırın."
        )


class MockBridge:
    """Test amaçlı: görev tipine göre sabit cevap döner."""

    def __init__(self, responses: dict):
        self.responses = responses

    def run_batch(self, tasks: list) -> dict:
        return {t["id"]: self.responses[t["type"]] for t in tasks}


def get_bridge(config: dict, workspace=None):
    llm = config.get("llm", {})
    provider = llm.get("provider", "inline")
    if provider == "inline":
        from .inline_skill import InlineSkillBridge
        if workspace is None:
            raise LLMError("inline provider için workspace gerekli")
        return InlineSkillBridge(workspace)
    if provider == "claude-cli":
        from .claude_cli import ClaudeCLIBridge
        return ClaudeCLIBridge(llm.get("model", ""), timeout=llm.get("timeout_seconds", 300))
    if provider in ("anthropic", "gemini", "perplexity"):
        from .api_clients import ApiBridge
        return ApiBridge(provider, llm)
    raise LLMError(f"bilinmeyen provider: {provider}")


def run_validated(bridge, tasks: list, max_retries: int = 1):
    """Görevleri çalıştırır, şema doğrular. Dönen: (ok: {id: result}, failed: [(task, errors)])."""
    ok, failed = {}, []
    pending = list(tasks)
    for _ in range(max_retries + 1):
        if not pending:
            break
        results = bridge.run_batch(pending)
        retry = []
        for t in pending:
            res = results.get(t["id"])
            errors = validate_result(t, res)
            if errors:
                retry.append((t, errors))
            else:
                ok[t["id"]] = res
        pending = [t for t, _ in retry]
        failed = retry
    return ok, failed
