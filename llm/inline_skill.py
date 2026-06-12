"""inline provider: görevleri pending_llm/ dosyalarına yazar, sohbetteki Claude işler.

Akış: run_batch → sonuç dosyası olanlar okunur; olmayanlar pending dosyası olarak
yazılır ve PendingLLMWork fırlatılır. Claude (skill talimatıyla) her görev için
<id>.result.json yazar ve komut yeniden çalıştırılır. Görev id'leri deterministik
olduğu için ikinci çalıştırma sonuçları bulur.
"""
import json
import os

from .bridge import PendingLLMWork
from .tasks import extract_json


class InlineSkillBridge:
    def __init__(self, workspace):
        self.ws = workspace

    def _write_pending(self, t):
        task_path = self.ws.path(f"pending_llm/{t['id']}.json")
        self.ws.write_json(f"pending_llm/{t['id']}.json", {
            **t,
            "_talimat": (
                "Bu bir LLM görevidir. 'prompt' alanındaki görevi uygula; cevabını YALNIZCA "
                "'schema'ya uyan saf JSON olarak, bu dosyanın yanına "
                f"{t['id']}.result.json adıyla yaz."
            ),
        })
        return task_path

    def run_batch(self, tasks: list) -> dict:
        results, missing = {}, []
        for t in tasks:
            result_path = self.ws.path(f"pending_llm/{t['id']}.result.json")
            if os.path.exists(result_path):
                raw = open(result_path, encoding="utf-8").read()
                try:
                    parsed = json.loads(raw)
                except json.JSONDecodeError:
                    parsed = extract_json(raw)
                if isinstance(parsed, dict):
                    results[t["id"]] = parsed
                    continue
                # Malformed and unrecoverable: rename bad file, re-queue task
                invalid_path = self.ws.path(f"pending_llm/{t['id']}.result.invalid.json")
                os.replace(result_path, invalid_path)
                task_path = self._write_pending(t)
                missing.append(task_path)
                continue
            task_path = self._write_pending(t)
            missing.append(task_path)
        if missing:
            raise PendingLLMWork(missing)
        return results
