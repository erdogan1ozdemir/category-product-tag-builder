"""LLM görev formatı: deterministik id, basit şema doğrulama, JSON ayıklama."""
import hashlib
import json
import re

_TYPES = {"list": list, "dict": dict, "str": str, "int": int}


def new_task(task_type: str, prompt: str, payload: dict = None, schema: dict = None) -> dict:
    """Görevi değiştiren her veri prompt veya payload içinde olmalı — id bu ikisinden türetilir."""
    payload_json = json.dumps(payload or {}, ensure_ascii=False, sort_keys=True)
    tid = hashlib.sha1(f"{task_type}|{prompt}|{payload_json}".encode("utf-8")).hexdigest()[:12]
    return {
        "id": tid,
        "type": task_type,
        "prompt": prompt,
        "payload": payload or {},
        "schema": schema or {},
    }


def validate_result(task: dict, result) -> list:
    if not isinstance(result, dict):
        return ["sonuç bir JSON nesnesi değil"]
    errors = []
    for key, typ in task.get("schema", {}).items():
        if key not in result:
            errors.append(f"eksik alan: {key}")
        elif not isinstance(result[key], _TYPES.get(typ, object)):
            errors.append(f"yanlış tip: {key} ({typ} bekleniyor)")
    return errors


def extract_json(text: str):
    if not text:
        return None
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    candidates = [fenced.group(1)] if fenced else []
    candidates.append(text.strip())
    m = re.search(r"\{.*\}", text, re.S)
    if m:
        candidates.append(m.group(0))
    for c in candidates:
        try:
            return json.loads(c)
        except (json.JSONDecodeError, TypeError):
            continue
    return None
