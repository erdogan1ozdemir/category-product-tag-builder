"""claude -p subprocess provider: lokal Claude Code kurulumunu kullanır, anahtar gerekmez."""
import json
import subprocess

from .bridge import LLMError
from .tasks import extract_json

SUFFIX = "\n\nYANIT KURALI: Yalnızca geçerli, saf JSON döndür; açıklama ekleme."


class ClaudeCLIBridge:
    def __init__(self, model: str = "", timeout: int = 300):
        self.model = model
        self.timeout = timeout

    def run_batch(self, tasks: list) -> dict:
        results = {}
        for t in tasks:
            cmd = ["claude", "-p", t["prompt"] + SUFFIX, "--output-format", "json"]
            if self.model:
                cmd += ["--model", self.model]
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout)
            except FileNotFoundError:
                raise LLMError("'claude' komutu bulunamadı — Claude Code kurulu mu? Alternatif: provider=inline")
            if proc.returncode != 0:
                raise LLMError(f"claude CLI hata verdi: {proc.stderr[:500]}")
            envelope = json.loads(proc.stdout)
            results[t["id"]] = extract_json(envelope.get("result", ""))
        return results
