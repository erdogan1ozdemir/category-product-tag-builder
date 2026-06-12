"""API anahtarlı provider'lar: Anthropic, Gemini, Perplexity — tek dosyada üç ince istemci."""
import requests

from .bridge import LLMError
from .tasks import extract_json

SUFFIX = "\n\nYANIT KURALI: Yalnızca geçerli, saf JSON döndür; açıklama ekleme."


def call_anthropic(prompt: str, key: str, model: str) -> str:
    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": model or "claude-opus-4-8", "max_tokens": 16000,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=120,
        )
    except requests.RequestException as e:
        raise LLMError(f"anthropic bağlantı hatası: {e}") from e
    if r.status_code != 200:
        raise LLMError(f"Anthropic API {r.status_code}: {r.text[:300]}")
    data = r.json()
    if data.get("stop_reason") == "max_tokens":
        raise LLMError("Anthropic yanıtı max_tokens'da kesildi — batch_size'ı düşürün")
    return data["content"][0]["text"]


def call_gemini(prompt: str, key: str, model: str) -> str:
    try:
        r = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model or 'gemini-2.0-flash'}:generateContent",
            headers={"x-goog-api-key": key},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=120,
        )
    except requests.RequestException as e:
        raise LLMError(f"gemini bağlantı hatası: {e}") from e
    if r.status_code != 200:
        raise LLMError(f"Gemini API {r.status_code}: {r.text[:300]}")
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]


def call_perplexity(prompt: str, key: str, model: str) -> str:
    try:
        r = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={"model": model or "sonar", "messages": [{"role": "user", "content": prompt}]},
            timeout=120,
        )
    except requests.RequestException as e:
        raise LLMError(f"perplexity bağlantı hatası: {e}") from e
    if r.status_code != 200:
        raise LLMError(f"Perplexity API {r.status_code}: {r.text[:300]}")
    return r.json()["choices"][0]["message"]["content"]


_CALLERS = {
    "anthropic": (call_anthropic, "anthropic_api_key", "model"),
    "gemini": (call_gemini, "gemini_api_key", "gemini_model"),
    "perplexity": (call_perplexity, "perplexity_api_key", "perplexity_model"),
}


class ApiBridge:
    def __init__(self, provider: str, llm_config: dict):
        caller, key_field, model_field = _CALLERS[provider]
        self.caller = caller
        self.key = llm_config.get(key_field, "")
        self.model = llm_config.get(model_field, "")
        if not self.key:
            raise LLMError(
                f"{provider} için API anahtarı boş — config.json'a {key_field} girin "
                "veya provider=inline kullanın."
            )

    def run_batch(self, tasks: list) -> dict:
        return {t["id"]: extract_json(self.caller(t["prompt"] + SUFFIX, self.key, self.model))
                for t in tasks}
