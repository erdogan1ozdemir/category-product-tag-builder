# Category Product Tag Builder — Implementasyon Planı

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Herhangi bir marka/sektör için facet havuzu üreten, ürün etiketleyen ve SEO kategori adayı çıkaran, Claude-yerel (anahtarsız) çalışabilen aracı sıfırdan kurmak.

**Architecture:** Üç değiştirilebilir katman (sources, llm, outputs) + sabit çekirdek (core, facets, tagger, seo, review). LLM işleri tek `LLMBridge` arayüzünden geçer; varsayılan `inline` provider iş dosyaları üretip sohbetteki Claude'a bırakır. v5'ten dört parça taşınır (normalizer, Trendyol istemcisi); gerisi temiz yazılır.

**Tech Stack:** Python 3.11+, requests, openpyxl, streamlit, pytest. Spec: `docs/superpowers/specs/2026-06-12-category-product-tag-builder-design.md`

**Çalışma dizini:** `/Users/Erdo/Desktop/Claude Projects/Özdilek/category-product-tag-builder`
**v5 kaynak klonu (taşıma için):** `/Users/Erdo/Desktop/Claude Projects/Özdilek/Category-generator-v5` — yoksa: `git clone https://github.com/emrekaynar26/Category-generator-v5.git`

**Genel kurallar:**
- Her görev sonunda `python -m pytest tests/ -q` tamamen yeşil olmalı.
- Commit mesajları Türkçe, conventional-commit önekli (`feat:`, `test:`, `docs:`, `chore:`).
- Tüm dosyalar UTF-8; Türkçe karakterli değerler test fixture'larında bilinçli kullanılır.

---

### Task 1: Proje iskeleti

**Files:**
- Create: `requirements.txt`, `config.example.json`, `.gitignore`, `conftest.py`
- Create: `core/__init__.py`, `sources/__init__.py`, `llm/__init__.py`, `facets/__init__.py`, `tagger/__init__.py`, `seo/__init__.py`, `outputs/__init__.py`, `review/__init__.py`, `tests/__init__.py`
- Create: `brands/_template.json`

- [ ] **Step 1: Dosyaları oluştur**

`requirements.txt`:
```
requests>=2.31
openpyxl>=3.1
streamlit>=1.50
pytest>=8.0
```

`config.example.json`:
```json
{
  "llm": {
    "provider": "inline",
    "model": "claude-opus-4-8",
    "anthropic_api_key": "",
    "gemini_api_key": "",
    "gemini_model": "gemini-2.0-flash",
    "perplexity_api_key": "",
    "perplexity_model": "sonar",
    "batch_size": 50
  },
  "dataforseo": { "login": "", "password": "" },
  "supabase": { "url": "", "service_key": "" },
  "seo": { "volume_threshold": 100, "two_facet_pairs": [], "exclude_groups": ["Beden", "Marka"] },
  "scraper": { "timeout": 20, "delay_seconds": 1.0 }
}
```

`.gitignore`:
```
__pycache__/
*.pyc
.venv/
config.json
workspace/
.pytest_cache/
.DS_Store
```

`conftest.py`:
```python
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
```

`brands/_template.json`:
```json
{
  "name": "Marka Adı",
  "slug": "marka-adi",
  "sector": "moda | kozmetik | banyo | telekom | ...",
  "site_domain": "marka.com.tr",
  "trendyol_brand": "Marka Adı",
  "trendyol_urls": [],
  "language": "tr",
  "notes": ""
}
```

Tüm `__init__.py` dosyaları boş oluşturulur:
```bash
for d in core sources llm facets tagger seo outputs review tests; do mkdir -p "$d" && touch "$d/__init__.py"; done
mkdir -p brands workspace docs
```

- [ ] **Step 2: Sanal ortam kur ve doğrula**

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -q -r requirements.txt && python -m pytest tests/ -q
```
Beklenen: `no tests ran` (hata yok).

- [ ] **Step 3: Commit**

```bash
git add -A && git commit -m "chore: proje iskeleti — paketler, config örneği, gitignore"
```

---

### Task 2: core/brand_profile.py — marka profili

**Files:**
- Create: `core/brand_profile.py`
- Test: `tests/test_brand_profile.py`

- [ ] **Step 1: Failing test yaz**

`tests/test_brand_profile.py`:
```python
import json
import pytest
from core.brand_profile import BrandProfile, load_brand


def _write(tmp_path, slug, data):
    (tmp_path / f"{slug}.json").write_text(json.dumps(data), encoding="utf-8")


def test_load_valid_brand(tmp_path):
    _write(tmp_path, "flormar", {"name": "Flormar", "slug": "flormar", "sector": "kozmetik"})
    b = load_brand("flormar", brands_dir=str(tmp_path))
    assert b.name == "Flormar"
    assert b.language == "tr"
    assert b.trendyol_urls == []


def test_missing_file_raises_helpful_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="init"):
        load_brand("yok", brands_dir=str(tmp_path))


def test_missing_required_field_raises(tmp_path):
    _write(tmp_path, "x", {"name": "X", "slug": "x"})
    with pytest.raises(ValueError, match="sector"):
        load_brand("x", brands_dir=str(tmp_path))


def test_bad_slug_raises(tmp_path):
    _write(tmp_path, "Büyük", {"name": "X", "slug": "Büyük", "sector": "moda"})
    with pytest.raises(ValueError, match="slug"):
        load_brand("Büyük", brands_dir=str(tmp_path))
```

- [ ] **Step 2: Çalıştır, FAIL gör** — `python -m pytest tests/test_brand_profile.py -q` → `ModuleNotFoundError`

- [ ] **Step 3: Implementasyon**

`core/brand_profile.py`:
```python
"""Marka profili: brands/<slug>.json yükleme ve doğrulama."""
import json
import os
import re
from dataclasses import dataclass, field, fields

REQUIRED = ("name", "slug", "sector")


@dataclass
class BrandProfile:
    name: str
    slug: str
    sector: str
    site_domain: str = ""
    trendyol_brand: str = ""
    trendyol_urls: list = field(default_factory=list)
    language: str = "tr"
    notes: str = ""


def load_brand(slug: str, brands_dir: str = "brands") -> BrandProfile:
    path = os.path.join(brands_dir, f"{slug}.json")
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Marka profili bulunamadı: {path} — 'python run.py init' ile oluşturun."
        )
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    missing = [k for k in REQUIRED if not data.get(k)]
    if missing:
        raise ValueError(f"Marka profilinde zorunlu alan eksik: {', '.join(missing)}")
    if not re.fullmatch(r"[a-z0-9-]+", data["slug"]):
        raise ValueError("slug yalnız küçük harf, rakam ve tire içerebilir")
    known = {f.name for f in fields(BrandProfile)}
    return BrandProfile(**{k: v for k, v in data.items() if k in known})
```

- [ ] **Step 4: Testler PASS** — `python -m pytest tests/test_brand_profile.py -q`

- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: marka profili yükleme ve doğrulama"`

---

### Task 3: core/state.py — workspace ve durum yönetimi

**Files:**
- Create: `core/state.py`
- Test: `tests/test_state.py`

- [ ] **Step 1: Failing test yaz**

`tests/test_state.py`:
```python
from core.state import Workspace


def test_ensure_creates_subdirs(tmp_path):
    ws = Workspace("flormar", root=str(tmp_path))
    ws.ensure()
    for d in ("input", "products", "pools", "pending_llm", "tagged", "combos", "exports"):
        assert (tmp_path / "flormar" / d).is_dir()


def test_jsonl_roundtrip_and_processed_ids(tmp_path):
    ws = Workspace("m", root=str(tmp_path))
    ws.ensure()
    ws.append_jsonl("products/products.jsonl", {"id": "a1", "name": "Ruj"})
    ws.append_jsonl("products/products.jsonl", {"id": "b2", "name": "Maskara"})
    rows = ws.read_jsonl("products/products.jsonl")
    assert [r["id"] for r in rows] == ["a1", "b2"]
    assert ws.processed_ids("products/products.jsonl") == {"a1", "b2"}


def test_read_jsonl_missing_returns_empty(tmp_path):
    ws = Workspace("m", root=str(tmp_path))
    assert ws.read_jsonl("yok.jsonl") == []


def test_json_roundtrip_atomic(tmp_path):
    ws = Workspace("m", root=str(tmp_path))
    ws.ensure()
    ws.write_json("pools/Ruj.json", {"arama_kelimesi": "Ruj"})
    assert ws.read_json("pools/Ruj.json")["arama_kelimesi"] == "Ruj"
    assert ws.read_json("yok.json", default={}) == {}
```

- [ ] **Step 2: FAIL gör** — `python -m pytest tests/test_state.py -q`

- [ ] **Step 3: Implementasyon**

`core/state.py`:
```python
"""Marka başına workspace/: dizinler, JSONL append/okuma, atomik JSON yazımı."""
import json
import os

SUBDIRS = ("input", "products", "pools", "pending_llm", "tagged", "combos", "exports")


class Workspace:
    def __init__(self, brand_slug: str, root: str = "workspace"):
        self.root = os.path.join(root, brand_slug)

    def ensure(self):
        for d in SUBDIRS:
            os.makedirs(os.path.join(self.root, d), exist_ok=True)
        return self

    def path(self, relpath: str) -> str:
        return os.path.join(self.root, relpath)

    def append_jsonl(self, relpath: str, obj: dict):
        p = self.path(relpath)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")

    def read_jsonl(self, relpath: str) -> list:
        p = self.path(relpath)
        if not os.path.exists(p):
            return []
        out = []
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
        return out

    def processed_ids(self, relpath: str, key: str = "id") -> set:
        return {r[key] for r in self.read_jsonl(relpath) if key in r}

    def write_json(self, relpath: str, obj):
        p = self.path(relpath)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        tmp = p + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
        os.replace(tmp, p)

    def read_json(self, relpath: str, default=None):
        p = self.path(relpath)
        if not os.path.exists(p):
            return default
        with open(p, encoding="utf-8") as f:
            return json.load(f)
```

- [ ] **Step 4: PASS** — `python -m pytest tests/test_state.py -q`

- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: workspace durum yönetimi (JSONL append, atomik JSON)"`

---

### Task 4: facets/normalizer.py — v5'ten taşıma

**Files:**
- Create: `facets/normalizer.py` (v5 kopyası)
- Test: `tests/test_normalizer.py`

- [ ] **Step 1: Failing test yaz**

Beklentiler v5 üzerinde canlı doğrulandı (2026-06-12), birebir bu davranış korunmalı.

`tests/test_normalizer.py`:
```python
from facets.normalizer import normalize_value_list, tr_lower, tr_title


def test_tr_lower_turkish_chars():
    assert tr_lower("İstanbul") == "istanbul"
    assert tr_lower("ISPARTA") == "ısparta"


def test_tr_title():
    assert tr_title("kırmızı çiçek") == "Kırmızı Çiçek"


def test_normalize_dedups_case_insensitive_and_strips():
    out = normalize_value_list(["kırmızı", "KIRMIZI", "Kırmızı ", "  ", "Lacivert"])
    assert out == ["Kırmızı", "Lacivert"]


def test_normalize_splits_composite_material():
    out = normalize_value_list(["%100 Pamuk", "Pamuk / Polyester"], group_name="Materyal")
    assert out == ["Pamuk", "Polyester"]
```

- [ ] **Step 2: FAIL gör** — `python -m pytest tests/test_normalizer.py -q`

- [ ] **Step 3: v5 dosyasını kopyala**

```bash
cp "/Users/Erdo/Desktop/Claude Projects/Özdilek/Category-generator-v5/product_tagger/normalization/normalizer.py" facets/normalizer.py
```
Dosya saf stdlib (re, unicodedata) kullanır — import değişikliği gerekmez. Dosya başındaki docstring'e şu not eklenir: `# Kaynak: Category-generator-v5/product_tagger/normalization/normalizer.py (birebir taşındı)`.

- [ ] **Step 4: PASS** — `python -m pytest tests/test_normalizer.py -q`

- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: TR-aware normalizer (v5'ten birebir taşındı)"`

---

### Task 5: llm/tasks.py — görev formatı ve sonuç doğrulama

**Files:**
- Create: `llm/tasks.py`
- Test: `tests/test_llm_tasks.py`

- [ ] **Step 1: Failing test yaz**

`tests/test_llm_tasks.py`:
```python
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
```

- [ ] **Step 2: FAIL gör** — `python -m pytest tests/test_llm_tasks.py -q`

- [ ] **Step 3: Implementasyon**

`llm/tasks.py`:
```python
"""LLM görev formatı: deterministik id, basit şema doğrulama, JSON ayıklama."""
import hashlib
import json
import re

_TYPES = {"list": list, "dict": dict, "str": str, "int": int}


def new_task(task_type: str, prompt: str, payload: dict = None, schema: dict = None) -> dict:
    tid = hashlib.sha1(f"{task_type}|{prompt}".encode("utf-8")).hexdigest()[:12]
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
```

- [ ] **Step 4: PASS** — `python -m pytest tests/test_llm_tasks.py -q`

- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: LLM görev formatı ve sonuç doğrulama"`

---

### Task 6: llm/bridge.py — arayüz, fabrika, mock, retry sarmalayıcı

**Files:**
- Create: `llm/bridge.py`
- Test: `tests/test_bridge.py`

- [ ] **Step 1: Failing test yaz**

`tests/test_bridge.py`:
```python
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
```

- [ ] **Step 2: FAIL gör** — `python -m pytest tests/test_bridge.py -q`

- [ ] **Step 3: Implementasyon**

`llm/bridge.py`:
```python
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
        return ClaudeCLIBridge(llm.get("model", ""))
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
```

- [ ] **Step 4: PASS** — `python -m pytest tests/test_bridge.py -q`

- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: LLM köprüsü — fabrika, mock provider, doğrulamalı çalıştırma"`

---

### Task 7: llm/inline_skill.py — inline (anahtarsız Claude) provider

**Files:**
- Create: `llm/inline_skill.py`
- Test: `tests/test_inline_skill.py`

- [ ] **Step 1: Failing test yaz**

`tests/test_inline_skill.py`:
```python
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
```

- [ ] **Step 2: FAIL gör** — `python -m pytest tests/test_inline_skill.py -q`

- [ ] **Step 3: Implementasyon**

`llm/inline_skill.py`:
```python
"""inline provider: görevleri pending_llm/ dosyalarına yazar, sohbetteki Claude işler.

Akış: run_batch → sonuç dosyası olanlar okunur; olmayanlar pending dosyası olarak
yazılır ve PendingLLMWork fırlatılır. Claude (skill talimatıyla) her görev için
<id>.result.json yazar ve komut yeniden çalıştırılır. Görev id'leri deterministik
olduğu için ikinci çalıştırma sonuçları bulur.
"""
import json
import os

from .bridge import PendingLLMWork


class InlineSkillBridge:
    def __init__(self, workspace):
        self.ws = workspace

    def run_batch(self, tasks: list) -> dict:
        results, missing = {}, []
        for t in tasks:
            result_path = self.ws.path(f"pending_llm/{t['id']}.result.json")
            if os.path.exists(result_path):
                with open(result_path, encoding="utf-8") as f:
                    results[t["id"]] = json.load(f)
                continue
            task_path = self.ws.path(f"pending_llm/{t['id']}.json")
            self.ws.write_json(f"pending_llm/{t['id']}.json", {
                **t,
                "_talimat": (
                    "Bu bir LLM görevidir. 'prompt' alanını uygula; cevabını YALNIZCA "
                    "'schema'ya uyan saf JSON olarak, bu dosyanın yanına "
                    f"{t['id']}.result.json adıyla yaz."
                ),
            })
            missing.append(task_path)
        if missing:
            raise PendingLLMWork(missing)
        return results
```

- [ ] **Step 4: PASS** — `python -m pytest tests/test_inline_skill.py -q`

- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: inline skill provider — pending_llm iş kuyruğu"`

---

### Task 8: llm/claude_cli.py + llm/api_clients.py — diğer provider'lar

Not: Spec üç ayrı API dosyası listeler; DRY gereği üç istemci tek `api_clients.py` içinde toplanır (her biri ~15 satır).

**Files:**
- Create: `llm/claude_cli.py`, `llm/api_clients.py`
- Test: `tests/test_providers.py`

- [ ] **Step 1: Failing test yaz**

`tests/test_providers.py`:
```python
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
```

- [ ] **Step 2: FAIL gör** — `python -m pytest tests/test_providers.py -q`

- [ ] **Step 3: Implementasyon**

`llm/claude_cli.py`:
```python
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
```

`llm/api_clients.py`:
```python
"""API anahtarlı provider'lar: Anthropic, Gemini, Perplexity — tek dosyada üç ince istemci."""
import requests

from .bridge import LLMError
from .tasks import extract_json

SUFFIX = "\n\nYANIT KURALI: Yalnızca geçerli, saf JSON döndür; açıklama ekleme."


def call_anthropic(prompt: str, key: str, model: str) -> str:
    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        json={"model": model or "claude-opus-4-8", "max_tokens": 4096,
              "messages": [{"role": "user", "content": prompt}]},
        timeout=120,
    )
    if r.status_code != 200:
        raise LLMError(f"Anthropic API {r.status_code}: {r.text[:300]}")
    return r.json()["content"][0]["text"]


def call_gemini(prompt: str, key: str, model: str) -> str:
    r = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model or 'gemini-2.0-flash'}:generateContent",
        params={"key": key},
        json={"contents": [{"parts": [{"text": prompt}]}]},
        timeout=120,
    )
    if r.status_code != 200:
        raise LLMError(f"Gemini API {r.status_code}: {r.text[:300]}")
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]


def call_perplexity(prompt: str, key: str, model: str) -> str:
    r = requests.post(
        "https://api.perplexity.ai/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json={"model": model or "sonar", "messages": [{"role": "user", "content": prompt}]},
        timeout=120,
    )
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
```

- [ ] **Step 4: PASS** — `python -m pytest tests/test_providers.py -q`

- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: claude-cli ve API provider'ları (Anthropic/Gemini/Perplexity)"`

---

### Task 9: sources/base.py + sources/generic_scraper.py

**Files:**
- Create: `sources/base.py`, `sources/generic_scraper.py`
- Create: `tests/fixtures/jsonld_product.html`, `tests/fixtures/og_product.html`, `tests/fixtures/plain_product.html`
- Test: `tests/test_generic_scraper.py`

- [ ] **Step 1: Fixture'ları oluştur**

`tests/fixtures/jsonld_product.html`:
```html
<!DOCTYPE html><html><head><title>Site</title>
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Product","name":"Mat Ruj 03 Kiremit",
 "description":"Uzun süre kalıcı mat ruj","brand":{"@type":"Brand","name":"Flormar"},
 "image":["https://cdn.example.com/ruj.jpg"],
 "offers":{"@type":"Offer","price":"199.90","priceCurrency":"TRY"},
 "additionalProperty":[{"@type":"PropertyValue","name":"Bitiş","value":"Mat"},
                       {"@type":"PropertyValue","name":"Ton","value":"Kiremit"}]}
</script></head><body></body></html>
```

`tests/fixtures/og_product.html`:
```html
<!DOCTYPE html><html><head><title>x</title>
<meta property="og:title" content="Seramik Lavabo 60 cm" />
<meta property="og:description" content="Beyaz, tezgah üstü lavabo" />
<meta property="og:image" content="https://cdn.example.com/lavabo.jpg" />
<meta property="product:price:amount" content="2450" />
</head><body></body></html>
```

`tests/fixtures/plain_product.html`:
```html
<!DOCTYPE html><html><head><title>Pamuklu Tişört | MarkaX</title></head><body>
<h1>Pamuklu Tişört</h1>
<table><tr><th>Materyal</th><td>Pamuk</td></tr><tr><th>Renk</th><td>Lacivert</td></tr></table>
</body></html>
```

- [ ] **Step 2: Failing test yaz**

`tests/test_generic_scraper.py`:
```python
import os
from sources.generic_scraper import parse_jsonld, parse_opengraph, parse_heuristic, scrape_product

FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def _read(name):
    with open(os.path.join(FIX, name), encoding="utf-8") as f:
        return f.read()


def test_jsonld_product():
    d = parse_jsonld(_read("jsonld_product.html"))
    assert d["name"] == "Mat Ruj 03 Kiremit"
    assert d["brand"] == "Flormar"
    assert d["attributes"] == {"Bitiş": "Mat", "Ton": "Kiremit"}
    assert d["price"] == "199.90"


def test_opengraph_fallback():
    d = parse_opengraph(_read("og_product.html"))
    assert d["name"] == "Seramik Lavabo 60 cm"
    assert d["images"] == ["https://cdn.example.com/lavabo.jpg"]


def test_heuristic_table_attributes():
    d = parse_heuristic(_read("plain_product.html"))
    assert d["name"] == "Pamuklu Tişört"
    assert d["attributes"] == {"Materyal": "Pamuk", "Renk": "Lacivert"}


def test_scrape_product_merges_with_priority():
    rec = scrape_product("https://example.com/p/1", html=_read("jsonld_product.html"))
    assert rec["name"] == "Mat Ruj 03 Kiremit"
    assert rec["url"] == "https://example.com/p/1"
    assert len(rec["id"]) == 12
```

- [ ] **Step 3: FAIL gör** — `python -m pytest tests/test_generic_scraper.py -q`

- [ ] **Step 4: Implementasyon**

`sources/base.py`:
```python
"""Ortak ürün kaydı yapısı. Tüm kaynaklar bu sözlük biçimini üretir."""
import hashlib

FIELDS = ("id", "url", "name", "category", "brand", "description", "attributes", "images", "price")


def product_record(url: str, **kw) -> dict:
    rec = {f: kw.get(f) for f in FIELDS}
    rec["url"] = url
    rec["id"] = hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
    rec["attributes"] = kw.get("attributes") or {}
    rec["images"] = kw.get("images") or []
    return rec
```

`sources/generic_scraper.py`:
```python
"""URL listesinden genel ürün ayıklama. Öncelik: JSON-LD > OpenGraph > sezgisel HTML."""
import json
import re
import time

import requests

from .base import product_record

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
}


def fetch_html(url: str, timeout: int = 20) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def _iter_jsonld_objects(html: str):
    for m in re.finditer(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', html, re.S | re.I):
        try:
            data = json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            continue
        stack = [data]
        while stack:
            obj = stack.pop()
            if isinstance(obj, list):
                stack.extend(obj)
            elif isinstance(obj, dict):
                if "@graph" in obj:
                    stack.extend(obj["@graph"])
                yield obj


def parse_jsonld(html: str):
    for obj in _iter_jsonld_objects(html):
        if str(obj.get("@type", "")).lower() != "product":
            continue
        brand = obj.get("brand")
        if isinstance(brand, dict):
            brand = brand.get("name")
        offers = obj.get("offers") or {}
        if isinstance(offers, list):
            offers = offers[0] if offers else {}
        images = obj.get("image") or []
        if isinstance(images, str):
            images = [images]
        attrs = {}
        for p in obj.get("additionalProperty", []) or []:
            if isinstance(p, dict) and p.get("name") and p.get("value") is not None:
                attrs[str(p["name"])] = str(p["value"])
        return {
            "name": obj.get("name"),
            "description": obj.get("description"),
            "brand": brand,
            "images": images,
            "price": str(offers.get("price")) if offers.get("price") is not None else None,
            "attributes": attrs,
        }
    return None


def _meta(html: str, prop: str):
    m = re.search(
        rf'<meta[^>]+(?:property|name)=["\']{re.escape(prop)}["\'][^>]+content=["\']([^"\']+)["\']',
        html, re.I,
    )
    return m.group(1).strip() if m else None


def parse_opengraph(html: str):
    name = _meta(html, "og:title")
    if not name:
        return None
    image = _meta(html, "og:image")
    return {
        "name": name,
        "description": _meta(html, "og:description"),
        "images": [image] if image else [],
        "price": _meta(html, "product:price:amount"),
        "attributes": {},
    }


def parse_heuristic(html: str):
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S | re.I)
    title = re.search(r"<title>(.*?)</title>", html, re.S | re.I)
    name = None
    if h1:
        name = re.sub(r"<[^>]+>", " ", h1.group(1)).strip()
    elif title:
        name = title.group(1).split("|")[0].strip()
    attrs = {}
    for row in re.finditer(r"<tr[^>]*>\s*<t[hd][^>]*>(.*?)</t[hd]>\s*<td[^>]*>(.*?)</td>", html, re.S | re.I):
        key = re.sub(r"<[^>]+>", "", row.group(1)).strip()
        val = re.sub(r"<[^>]+>", "", row.group(2)).strip()
        if key and val:
            attrs[key] = val
    for pair in re.finditer(r"<dt[^>]*>(.*?)</dt>\s*<dd[^>]*>(.*?)</dd>", html, re.S | re.I):
        key = re.sub(r"<[^>]+>", "", pair.group(1)).strip()
        val = re.sub(r"<[^>]+>", "", pair.group(2)).strip()
        if key and val:
            attrs[key] = val
    return {"name": name, "description": None, "images": [], "price": None, "attributes": attrs}


def scrape_product(url: str, html: str = None, timeout: int = 20) -> dict:
    html = html if html is not None else fetch_html(url, timeout=timeout)
    layers = [parse_heuristic(html), parse_opengraph(html), parse_jsonld(html)]
    merged = {}
    for layer in layers:
        if not layer:
            continue
        for k, v in layer.items():
            if v:
                merged[k] = v
    return product_record(url, **merged)


def collect_from_urls(urls: list, workspace, delay: float = 1.0, timeout: int = 20) -> dict:
    """URL listesini gez; işlenmişleri atla; hataları errors.jsonl'a yaz."""
    done = workspace.processed_ids("products/products.jsonl")
    counts = {"yeni": 0, "atlandı": 0, "hata": 0}
    for url in urls:
        from .base import product_record as _pr
        pid = _pr(url)["id"]
        if pid in done:
            counts["atlandı"] += 1
            continue
        try:
            rec = scrape_product(url, timeout=timeout)
            if not rec.get("name"):
                raise ValueError("ürün adı ayıklanamadı")
            workspace.append_jsonl("products/products.jsonl", rec)
            counts["yeni"] += 1
        except Exception as e:
            workspace.append_jsonl("errors.jsonl", {"stage": "collect", "url": url, "error": str(e)})
            counts["hata"] += 1
        time.sleep(delay)
    return counts
```

- [ ] **Step 5: PASS** — `python -m pytest tests/test_generic_scraper.py -q`

- [ ] **Step 6: Commit** — `git add -A && git commit -m "feat: genel scraper — JSON-LD/OG/sezgisel üç katmanlı ayıklama"`

---

### Task 9b: Playwright render fallback (kapsam eki — kullanıcı kararı 2026-06-12)

JS-ağır sitelerde statik çekim ürün adı veremezse headless Chromium ile render edilip aynı üç katman yeniden denenir.

**Files:**
- Modify: `requirements.txt` (+ `playwright>=1.50`), `config.example.json` (`scraper.playwright_fallback: true`)
- Modify: `sources/generic_scraper.py`
- Test: `tests/test_generic_scraper.py` (ekleme)

- [ ] **Step 1: Failing test yaz** (tests/test_generic_scraper.py'ye ekle)

```python
def test_render_fallback_used_when_static_has_no_name(tmp_path, monkeypatch):
    from core.state import Workspace
    from sources import generic_scraper as gs
    ws = Workspace("m", root=str(tmp_path)).ensure()
    monkeypatch.setattr(gs, "fetch_html", lambda url, timeout=20: "<html><body>bos</body></html>")
    monkeypatch.setattr(gs, "fetch_html_rendered", lambda url, timeout=30: _read("jsonld_product.html"))
    counts = gs.collect_from_urls(["https://spa.example.com/p/1"], ws, delay=0, render_fallback=True)
    assert counts == {"yeni": 1, "atlandı": 0, "hata": 0, "render": 1}
    assert ws.read_jsonl("products/products.jsonl")[0]["name"] == "Mat Ruj 03 Kiremit"


def test_render_fallback_disabled_logs_error(tmp_path, monkeypatch):
    from core.state import Workspace
    from sources import generic_scraper as gs
    ws = Workspace("m", root=str(tmp_path)).ensure()
    monkeypatch.setattr(gs, "fetch_html", lambda url, timeout=20: "<html><body>bos</body></html>")
    counts = gs.collect_from_urls(["https://spa.example.com/p/1"], ws, delay=0, render_fallback=False)
    assert counts["hata"] == 1
```

- [ ] **Step 2: FAIL gör**

- [ ] **Step 3: Implementasyon**

`sources/generic_scraper.py`'ye eklenir:

```python
def fetch_html_rendered(url: str, timeout: int = 30) -> str:
    """Headless Chromium ile sayfayı render edip HTML döner (JS-ağır siteler için)."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise RuntimeError(
            "playwright kurulu değil — pip install playwright && playwright install chromium"
        )
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(user_agent=HEADERS["User-Agent"],
                                    locale="tr-TR")
            page.goto(url, timeout=timeout * 1000, wait_until="domcontentloaded")
            try:
                page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass
            html = page.content()
        finally:
            browser.close()
    return html
```

`collect_from_urls` imzası `render_fallback: bool = True` parametresi alır; sayaçlara `"render": 0` eklenir. Akış: statik `scrape_product` dene → istek hatası VEYA `name` boşsa ve `render_fallback` açıksa → `fetch_html_rendered` ile HTML alıp `scrape_product(url, html=rendered)` dene (başarıda `render` sayacı artar) → hâlâ başarısızsa `errors.jsonl`.

- [ ] **Step 4: PASS** — tüm takım yeşil

- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: Playwright render fallback — JS-ağır siteler"`

Not: `stage_collect` (Task 18) `config.scraper.playwright_fallback` değerini `collect_from_urls`'a geçirmelidir.

### Task 10: sources/trendyol.py — v5'ten taşıma

**Files:**
- Create: `sources/trendyol.py`
- Test: `tests/test_trendyol.py`

- [ ] **Step 1: Failing test yaz**

`tests/test_trendyol.py`:
```python
from unittest.mock import patch, MagicMock
from sources.trendyol import fetch_aggregations, path_model_from_url


def test_path_model_from_url():
    assert path_model_from_url("https://www.trendyol.com/abiye-x-c56?pi=2") == "abiye-x-c56"


def test_fetch_aggregations_parses_groups():
    resp = MagicMock(status_code=200)
    resp.json.return_value = {"aggregation": [
        {"title": "Renk", "values": [{"text": "Kırmızı"}, {"text": "Siyah"}]},
        {"title": "Boş", "values": []},
    ]}
    with patch("sources.trendyol.requests.get", return_value=resp):
        out = fetch_aggregations("https://www.trendyol.com/abiye-x-c56")
    assert out == {"Renk": ["Kırmızı", "Siyah"]}


def test_fetch_aggregations_network_error_returns_empty():
    with patch("sources.trendyol.requests.get", side_effect=Exception("boom")):
        assert fetch_aggregations("https://www.trendyol.com/abiye-x-c56") == {}
```

- [ ] **Step 2: FAIL gör** — `python -m pytest tests/test_trendyol.py -q`

- [ ] **Step 3: Implementasyon**

`sources/trendyol.py` (çekirdek kod aşağıda; SEO landing fonksiyonları v5'ten kopyalanır):
```python
"""Trendyol kaynak adaptörü.

Aggregation kodu v5 pool_creator/scripts/trendyol_seo_landing_enricher.py'den
uyarlandı (fetch_landing_aggregation). SEO landing ayıklama fonksiyonları aynı
dosyadan birebir kopyalanır (aşağıdaki kopyalama adımı).
"""
import re
from urllib.parse import urlparse

import requests

TRENDYOL_BASE = "https://www.trendyol.com"
TRENDYOL_AGGREGATION_URL = (
    "https://apigw.trendyol.com/discovery-sfint-search-service/api/search/aggregations"
)
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


def path_model_from_url(url: str) -> str:
    return urlparse(url).path.strip("/")


def fetch_aggregations(trendyol_url: str, timeout: int = 20) -> dict:
    """Trendyol kategori/marka sayfası URL'sinden facet grup → değer listesi döner."""
    path_model = path_model_from_url(trendyol_url)
    if not path_model:
        return {}
    params = {
        "promotionSearch": "false", "stickyShellNavigation": "false",
        "loadPromoNavigationHeader": "false", "isDynamicRenderingAgent": "true",
        "channelId": "1", "pi": "1", "pageSize": "24",
        "pathModel": path_model, "sst": "SCORE", "countryCode": "TR",
    }
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json,text/plain,*/*",
        "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
        "Origin": TRENDYOL_BASE,
        "Referer": f"{TRENDYOL_BASE}/{path_model}",
    }
    try:
        resp = requests.get(TRENDYOL_AGGREGATION_URL, params=params, headers=headers, timeout=timeout)
    except Exception:
        return {}
    if resp.status_code != 200:
        return {}
    try:
        aggs = resp.json().get("aggregation", [])
    except Exception:
        return {}
    out = {}
    for agg in aggs:
        title = agg.get("title")
        values = [v.get("text") for v in agg.get("values", []) if v.get("text")]
        if title and values:
            out[title] = values[:30]
    return out
```

Ardından v5'ten SEO landing fonksiyonları dosya sonuna kopyalanır — kaynak: `Category-generator-v5/pool_creator/scripts/trendyol_seo_landing_enricher.py` içinden şu öğeler **birebir**: `SEO_USER_AGENTS` sabiti, `_slug_text`, `_json_from_script_assignment`, `_walk_landing_items`, `_is_relevant_landing`, `_fetch_html`, `extract_category_seo_landings` (satır 80–203). İçlerindeki `from product_tagger.normalization import ...` importu **silinir** (bu fonksiyonlar onu kullanmaz); başka uyarlama gerekmez.

- [ ] **Step 4: PASS** — `python -m pytest tests/test_trendyol.py -q`

- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: Trendyol kaynak adaptörü (v5'ten uyarlandı)"`

---

### Task 11: facets/taxonomy.py — sektöre göre facet grubu önerisi

**Files:**
- Create: `facets/taxonomy.py`
- Test: `tests/test_taxonomy.py`

- [ ] **Step 1: Failing test yaz**

`tests/test_taxonomy.py`:
```python
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
```

- [ ] **Step 2: FAIL gör** — `python -m pytest tests/test_taxonomy.py -q`

- [ ] **Step 3: Implementasyon**

`facets/taxonomy.py`:
```python
"""Sektöre uygun facet (filtre) grubu taksonomisi önerisi — LLM görevi."""
from llm.bridge import run_validated
from llm.tasks import new_task

PROMPT = """Sen bir e-ticaret kategori yönetimi uzmanısın.
Sektör: {sector}
Kaynaklardan toplanan ham filtre grubu adları: {raw_groups}

Görev: Bu sektör için müşterinin ürün filtrelemede gerçekten kullanacağı facet
gruplarını öner. Ham listedeki pazarlama/platform gruplarını (Kampanya, Kargo,
Satıcı gibi) ELE; eksik ama sektörde standart olan grupları EKLE.
JSON formatı: {{"groups": [{{"group": "Grup Adı", "description": "kısa açıklama"}}]}}"""


def build_taxonomy_task(sector: str, raw_groups: list) -> dict:
    prompt = PROMPT.format(sector=sector, raw_groups=", ".join(sorted(set(raw_groups))) or "(yok)")
    return new_task("taxonomy_proposal", prompt, schema={"groups": "list"})


def propose_taxonomy(sector: str, raw_groups: list, bridge) -> dict:
    task = build_taxonomy_task(sector, raw_groups)
    ok, failed = run_validated(bridge, [task])
    if failed:
        raise RuntimeError(f"Taksonomi önerisi doğrulanamadı: {failed[0][1]}")
    return ok[task["id"]]
```

- [ ] **Step 4: PASS** — `python -m pytest tests/test_taxonomy.py -q`

- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: sektöre göre facet taksonomi önerisi"`

---

### Task 12: facets/pool_builder.py — havuz birleştirme

**Files:**
- Create: `facets/pool_builder.py`
- Test: `tests/test_pool_builder.py`

- [ ] **Step 1: Failing test yaz**

`tests/test_pool_builder.py`:
```python
from facets.pool_builder import build_pool, pool_groups


def test_build_pool_merges_normalizes_and_keeps_v5_format():
    sources = [
        {"Renk": ["kırmızı", "KIRMIZI"], "Kampanya": ["2 al 1 öde"]},
        {"Renk": ["Lacivert"], "Bitiş": ["Mat"]},
    ]
    pool = build_pool("Ruj", sources, allowed_groups=["Renk", "Bitiş"])
    havuz = pool["gap_analizi"]["birlesik_filtre_havuzu"]
    assert pool["arama_kelimesi"] == "Ruj"
    assert havuz["Renk"] == ["Kırmızı", "Lacivert"]
    assert havuz["Bitiş"] == ["Mat"]
    assert "Kampanya" not in havuz


def test_build_pool_without_allowed_groups_keeps_all():
    pool = build_pool("Ruj", [{"Renk": ["Siyah"], "Doku": ["Krem"]}], allowed_groups=None)
    assert set(pool_groups(pool)) == {"Renk", "Doku"}


def test_empty_groups_dropped():
    pool = build_pool("Ruj", [{"Renk": ["  "]}], allowed_groups=None)
    assert pool_groups(pool) == []
```

- [ ] **Step 2: FAIL gör** — `python -m pytest tests/test_pool_builder.py -q`

- [ ] **Step 3: Implementasyon**

`facets/pool_builder.py`:
```python
"""Kaynak facet verilerini birleştirip normalize ederek v5 formatında havuz üretir."""
from collections import defaultdict

from .normalizer import normalize_value_list, tr_lower


def build_pool(category: str, source_maps: list, allowed_groups=None) -> dict:
    merged = defaultdict(list)
    for source in source_maps:
        for group, values in (source or {}).items():
            merged[group].extend(values)
    if allowed_groups is not None:
        allowed = {tr_lower(g) for g in allowed_groups}
        merged = {g: v for g, v in merged.items() if tr_lower(g) in allowed}
    havuz = {}
    for group, values in merged.items():
        normalized = normalize_value_list(values, group_name=group)
        if normalized:
            havuz[group] = sorted(normalized, key=tr_lower)
    return {"arama_kelimesi": category, "gap_analizi": {"birlesik_filtre_havuzu": havuz}}


def pool_groups(pool: dict) -> list:
    return list(pool.get("gap_analizi", {}).get("birlesik_filtre_havuzu", {}).keys())


def pool_values(pool: dict) -> dict:
    return pool.get("gap_analizi", {}).get("birlesik_filtre_havuzu", {})
```

- [ ] **Step 4: PASS** — `python -m pytest tests/test_pool_builder.py -q`

- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: havuz birleştirici — v5 formatı korunarak"`

---

### Task 13: facets/quality_checker.py — LLM kalite denetimi (slim yeniden yazım)

Not: v5'teki 483 satırlık denetçi Gemini'ye sıkı bağlı; spec gereği LLMBridge üzerinden çalışan sade bir yeniden yazım yapılır (remove + merge operasyonları).

**Files:**
- Create: `facets/quality_checker.py`
- Test: `tests/test_quality_checker.py`

- [ ] **Step 1: Failing test yaz**

`tests/test_quality_checker.py`:
```python
from facets.quality_checker import apply_quality, check_pool
from facets.pool_builder import build_pool
from llm.bridge import MockBridge


def _pool():
    return build_pool("Ruj", [{"Renk": ["Kırmızı", "Kirmizi", "Junk123"], "Bitiş": ["Mat"]}], None)


def test_apply_quality_removes_and_merges():
    result = {"remove": {"Renk": ["Junk123"]}, "merge": {"Renk": {"Kirmizi": "Kırmızı"}}}
    cleaned = apply_quality(_pool(), result)
    assert cleaned["gap_analizi"]["birlesik_filtre_havuzu"]["Renk"] == ["Kırmızı"]
    assert cleaned["gap_analizi"]["birlesik_filtre_havuzu"]["Bitiş"] == ["Mat"]


def test_apply_quality_ignores_unknown_groups():
    cleaned = apply_quality(_pool(), {"remove": {"Yok": ["x"]}, "merge": {}})
    assert "Yok" not in cleaned["gap_analizi"]["birlesik_filtre_havuzu"]


def test_check_pool_via_bridge():
    b = MockBridge({"pool_quality": {"remove": {"Renk": ["Junk123"]}, "merge": {}}})
    cleaned = check_pool("Ruj", _pool(), b)
    assert "Junk123" not in cleaned["gap_analizi"]["birlesik_filtre_havuzu"]["Renk"]
```

- [ ] **Step 2: FAIL gör** — `python -m pytest tests/test_quality_checker.py -q`

- [ ] **Step 3: Implementasyon**

`facets/quality_checker.py`:
```python
"""Havuz kalite denetimi: LLM'den remove/merge önerisi alır, deterministik uygular."""
import json

from llm.bridge import run_validated
from llm.tasks import new_task

from .normalizer import tr_lower
from .pool_builder import pool_values

PROMPT = """Sen bir e-ticaret veri kalitesi uzmanısın. Aşağıda '{category}' kategorisinin
facet havuzu var. Görevlerin:
1. Anlamsız/çöp değerleri tespit et (ürün kodu, rastgele sayı, pazarlama metni).
2. Aynı anlama gelen değerleri birleştir (yazım hatası, eşanlamlı) — doğru yazımı hedef yap.
Havuz: {pool_json}
JSON formatı: {{"remove": {{"Grup": ["değer"]}}, "merge": {{"Grup": {{"yanlış": "doğru"}}}}}}
Yalnızca havuzda gerçekten geçen grup ve değerleri kullan."""


def build_quality_task(category: str, pool: dict) -> dict:
    prompt = PROMPT.format(category=category,
                           pool_json=json.dumps(pool_values(pool), ensure_ascii=False))
    return new_task("pool_quality", prompt, schema={"remove": "dict", "merge": "dict"})


def apply_quality(pool: dict, result: dict) -> dict:
    havuz = {g: list(v) for g, v in pool_values(pool).items()}
    for group, values in (result.get("remove") or {}).items():
        if group in havuz:
            drop = {tr_lower(v) for v in values}
            havuz[group] = [v for v in havuz[group] if tr_lower(v) not in drop]
    for group, mapping in (result.get("merge") or {}).items():
        if group not in havuz:
            continue
        repl = {tr_lower(k): v for k, v in mapping.items()}
        seen, out = set(), []
        for v in havuz[group]:
            v = repl.get(tr_lower(v), v)
            if tr_lower(v) not in seen:
                seen.add(tr_lower(v))
                out.append(v)
        havuz[group] = out
    havuz = {g: v for g, v in havuz.items() if v}
    return {**pool, "gap_analizi": {**pool["gap_analizi"], "birlesik_filtre_havuzu": havuz}}


def check_pool(category: str, pool: dict, bridge) -> dict:
    task = build_quality_task(category, pool)
    ok, failed = run_validated(bridge, [task])
    if failed:
        raise RuntimeError(f"Kalite denetimi doğrulanamadı: {failed[0][1]}")
    return apply_quality(pool, ok[task["id"]])
```

- [ ] **Step 4: PASS** — `python -m pytest tests/test_quality_checker.py -q`

- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: havuz kalite denetimi — LLMBridge üzerinden remove/merge"`

---

### Task 14: tagger/product_tagger.py + tagger/batch.py

**Files:**
- Create: `tagger/product_tagger.py`, `tagger/batch.py`
- Test: `tests/test_tagger.py`

- [ ] **Step 1: Failing test yaz**

`tests/test_tagger.py`:
```python
from core.state import Workspace
from facets.pool_builder import build_pool
from llm.bridge import MockBridge
from tagger.product_tagger import deterministic_tags
from tagger.batch import tag_products


def _pool():
    return build_pool("Ruj", [{"Bitiş": ["Mat", "Parlak"], "Ton": ["Kiremit", "Nude"]}], None)


def test_deterministic_finds_values_in_text():
    p = {"name": "Flormar Mat Ruj Kiremit", "description": "", "attributes": {}}
    tags = deterministic_tags(p, _pool())
    assert tags == {"Bitiş": "Mat", "Ton": "Kiremit"}


def test_deterministic_no_guess_when_absent():
    p = {"name": "Flormar Ruj", "description": "", "attributes": {}}
    assert deterministic_tags(p, _pool()) == {}


def test_tag_products_merges_llm_fills_and_resumes(tmp_path):
    ws = Workspace("m", root=str(tmp_path)).ensure()
    ws.append_jsonl("products/products.jsonl",
                    {"id": "p1", "name": "Mat Ruj", "category": "Ruj", "description": "", "attributes": {}})
    bridge = MockBridge({"product_tagging": {"products": [{"id": "p1", "tags": {"Ton": "Nude"}}]}})
    n = tag_products(ws, {"Ruj": _pool()}, bridge, batch_size=10)
    assert n == 1
    row = ws.read_jsonl("tagged/tagged.jsonl")[0]
    assert row["tags"]["Bitiş"] == {"value": "Mat", "source": "deterministik"}
    assert row["tags"]["Ton"] == {"value": "Nude", "source": "llm"}
    assert tag_products(ws, {"Ruj": _pool()}, bridge) == 0
```

- [ ] **Step 2: FAIL gör** — `python -m pytest tests/test_tagger.py -q`

- [ ] **Step 3: Implementasyon**

`tagger/product_tagger.py`:
```python
"""Ürün etiketleme: önce deterministik metin eşleme, boşlukları LLM doldurur."""
import json

from facets.normalizer import tr_lower
from facets.pool_builder import pool_values
from llm.tasks import new_task


def _product_text(product: dict) -> str:
    parts = [product.get("name") or "", product.get("description") or ""]
    parts += [f"{k} {v}" for k, v in (product.get("attributes") or {}).items()]
    return tr_lower(" ".join(parts))


def deterministic_tags(product: dict, pool: dict) -> dict:
    text = _product_text(product)
    tags = {}
    for group, values in pool_values(pool).items():
        for value in sorted(values, key=len, reverse=True):
            if tr_lower(value) in text:
                tags[group] = value
                break
    return tags


PROMPT = """Sen bir e-ticaret ürün etiketleme uzmanısın. Her ürün için, SADECE verilen
havuz değerlerinden seçerek eksik facet'leri doldur. Üründen emin olamadığın
facet'i BOŞ BIRAK — tahmin etme, havuz dışı değer üretme.
Kategori: {category}
Havuz: {pool_json}
Ürünler (eksik gruplar 'missing' alanında): {products_json}
JSON formatı: {{"products": [{{"id": "...", "tags": {{"Grup": "Değer"}}}}]}}"""


def build_tagging_task(category: str, pool: dict, items: list) -> dict:
    prompt = PROMPT.format(
        category=category,
        pool_json=json.dumps(pool_values(pool), ensure_ascii=False),
        products_json=json.dumps(items, ensure_ascii=False),
    )
    return new_task("product_tagging", prompt, schema={"products": "list"})
```

`tagger/batch.py`:
```python
"""Toplu etiketleme: resume destekli, hatalar errors.jsonl'a düşer."""
from llm.bridge import run_validated

from .product_tagger import build_tagging_task, deterministic_tags


def _chunks(seq, size):
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


def tag_products(ws, pools_by_category: dict, bridge, batch_size: int = 50) -> int:
    done = ws.processed_ids("tagged/tagged.jsonl")
    pending = [p for p in ws.read_jsonl("products/products.jsonl") if p["id"] not in done]
    written = 0
    by_cat = {}
    for p in pending:
        cat = p.get("category") or "Genel"
        by_cat.setdefault(cat, []).append(p)
    for cat, products in by_cat.items():
        pool = pools_by_category.get(cat)
        if pool is None:
            for p in products:
                ws.append_jsonl("errors.jsonl", {"stage": "tag", "id": p["id"],
                                                 "error": f"havuz yok: {cat}"})
            continue
        det = {p["id"]: deterministic_tags(p, pool) for p in products}
        from facets.pool_builder import pool_values
        all_groups = set(pool_values(pool))
        need_llm = []
        for p in products:
            missing = sorted(all_groups - set(det[p["id"]]))
            if missing:
                need_llm.append({"id": p["id"], "name": p.get("name"),
                                 "description": (p.get("description") or "")[:500],
                                 "attributes": p.get("attributes") or {}, "missing": missing})
        llm_tags = {}
        if need_llm:
            tasks = [build_tagging_task(cat, pool, chunk) for chunk in _chunks(need_llm, batch_size)]
            ok, failed = run_validated(bridge, tasks)
            for result in ok.values():
                for row in result.get("products", []):
                    llm_tags[row.get("id")] = row.get("tags") or {}
            for task, errors in failed:
                ws.append_jsonl("errors.jsonl", {"stage": "tag", "task_id": task["id"],
                                                 "error": "; ".join(errors)})
        valid = {g: {v for v in vals} for g, vals in pool_values(pool).items()}
        for p in products:
            tags = {g: {"value": v, "source": "deterministik"} for g, v in det[p["id"]].items()}
            for g, v in llm_tags.get(p["id"], {}).items():
                if g in valid and v in valid[g] and g not in tags:
                    tags[g] = {"value": v, "source": "llm"}
            ws.append_jsonl("tagged/tagged.jsonl",
                            {"id": p["id"], "url": p.get("url"), "name": p.get("name"),
                             "category": cat, "tags": tags})
            written += 1
    return written
```

- [ ] **Step 4: PASS** — `python -m pytest tests/test_tagger.py -q`

- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: ürün etiketleme — deterministik + LLM boşluk doldurma, resume"`

---

### Task 15: seo/cross_join.py + seo/volume.py

**Files:**
- Create: `seo/cross_join.py`, `seo/volume.py`
- Test: `tests/test_seo.py`

- [ ] **Step 1: Failing test yaz**

`tests/test_seo.py`:
```python
from unittest.mock import patch, MagicMock
from facets.pool_builder import build_pool
from seo.cross_join import generate_combos
from seo.volume import apply_threshold, export_manual_csv, import_volumes_csv, fetch_volumes_dataforseo


def _pool():
    return build_pool("Abiye", [{"Renk": ["Kırmızı"], "Yaka Tipi": ["V Yaka"], "Beden": ["36"]}], None)


def test_generate_combos_single_and_pairs_excluding_groups():
    combos = generate_combos("Abiye", _pool(), exclude_groups=["Beden"],
                             two_facet_pairs=[["Renk", "Yaka Tipi"]])
    keywords = [c["combo"] for c in combos]
    assert "Kırmızı Abiye" in keywords
    assert "V Yaka Abiye" in keywords
    assert "Kırmızı V Yaka Abiye" in keywords
    assert all("36" not in k for k in keywords)


def test_apply_threshold_marks_decision():
    combos = [{"combo": "Kırmızı Abiye"}, {"combo": "Mor Abiye"}]
    out = apply_threshold(combos, {"Kırmızı Abiye": 500, "Mor Abiye": 10}, threshold=100)
    assert out[0]["decision"] == "kategori"
    assert out[1]["decision"] == "filtre"


def test_manual_csv_roundtrip(tmp_path):
    path = str(tmp_path / "v.csv")
    export_manual_csv([{"combo": "Kırmızı Abiye"}], path)
    content = open(path, encoding="utf-8").read()
    assert "Kırmızı Abiye" in content
    open(path, "w", encoding="utf-8").write("combo,volume\nKırmızı Abiye,250\n")
    assert import_volumes_csv(path) == {"Kırmızı Abiye": 250}


def test_dataforseo_parses_volumes():
    resp = MagicMock(status_code=200)
    resp.json.return_value = {"tasks": [{"result": [
        {"keyword": "kırmızı abiye", "search_volume": 5400}]}]}
    with patch("seo.volume.requests.post", return_value=resp):
        out = fetch_volumes_dataforseo(["kırmızı abiye"], "user", "pass")
    assert out == {"kırmızı abiye": 5400}
```

- [ ] **Step 2: FAIL gör** — `python -m pytest tests/test_seo.py -q`

- [ ] **Step 3: Implementasyon**

`seo/cross_join.py`:
```python
"""Kategori × facet kombinasyon türetme (atomik kategori adayları)."""
from facets.pool_builder import pool_values


def generate_combos(category: str, pool: dict, exclude_groups=None, two_facet_pairs=None) -> list:
    havuz = pool_values(pool)
    exclude = set(exclude_groups or [])
    combos, seen = [], set()

    def _add(combo, parts):
        if combo not in seen:
            seen.add(combo)
            combos.append({"combo": combo, "parts": parts})

    for group, values in havuz.items():
        if group in exclude:
            continue
        for value in values:
            _add(f"{value} {category}", {group: value})
    for pair in (two_facet_pairs or []):
        g1, g2 = pair[0], pair[1]
        for v1 in havuz.get(g1, []):
            for v2 in havuz.get(g2, []):
                _add(f"{v1} {v2} {category}", {g1: v1, g2: v2})
    return combos
```

`seo/volume.py`:
```python
"""Aranma hacmi: DataForSEO (anahtar varsa) veya manuel CSV içe aktarma."""
import csv

import requests

DFS_URL = "https://api.dataforseo.com/v3/keywords_data/google_ads/search_volume/live"


def fetch_volumes_dataforseo(keywords: list, login: str, password: str,
                             location_code: int = 2792, language_code: str = "tr") -> dict:
    """location_code 2792 = Türkiye."""
    payload = [{"keywords": keywords, "location_code": location_code,
                "language_code": language_code}]
    resp = requests.post(DFS_URL, auth=(login, password), json=payload, timeout=120)
    if resp.status_code != 200:
        raise RuntimeError(f"DataForSEO {resp.status_code}: {resp.text[:300]}")
    out = {}
    for task in resp.json().get("tasks", []):
        for row in (task.get("result") or []):
            if row.get("keyword") is not None:
                out[row["keyword"]] = row.get("search_volume") or 0
    return out


def export_manual_csv(combos: list, path: str):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["combo", "volume"])
        for c in combos:
            w.writerow([c["combo"], ""])


def import_volumes_csv(path: str) -> dict:
    out = {}
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                out[row["combo"]] = int(row["volume"])
            except (KeyError, TypeError, ValueError):
                continue
    return out


def apply_threshold(combos: list, volumes: dict, threshold: int) -> list:
    out = []
    for c in combos:
        vol = volumes.get(c["combo"])
        decision = "kategori" if (vol or 0) >= threshold else "filtre"
        out.append({**c, "volume": vol, "decision": decision})
    return out
```

- [ ] **Step 4: PASS** — `python -m pytest tests/test_seo.py -q`

- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: kombinasyon türetme + aranma hacmi (DataForSEO/manuel CSV)"`

---

### Task 16: outputs/ — json, excel, supabase sink'leri

**Files:**
- Create: `outputs/json_sink.py`, `outputs/excel_sink.py`, `outputs/supabase_sink.py`
- Test: `tests/test_outputs.py`

- [ ] **Step 1: Failing test yaz**

`tests/test_outputs.py`:
```python
import json
from unittest.mock import patch, MagicMock
import openpyxl
from core.state import Workspace
from facets.pool_builder import build_pool
from outputs.json_sink import export_json
from outputs.excel_sink import export_excel
from outputs.supabase_sink import SupabaseSink


def _ws(tmp_path):
    ws = Workspace("m", root=str(tmp_path)).ensure()
    ws.write_json("pools/Ruj.json", build_pool("Ruj", [{"Bitiş": ["Mat"]}], None))
    ws.append_jsonl("tagged/tagged.jsonl", {"id": "p1", "url": "u", "name": "Mat Ruj",
                                            "category": "Ruj",
                                            "tags": {"Bitiş": {"value": "Mat", "source": "deterministik"}}})
    ws.write_json("combos/combos.json",
                  [{"combo": "Mat Ruj", "volume": 900, "decision": "kategori"}])
    return ws


def test_export_json_consolidates(tmp_path):
    ws = _ws(tmp_path)
    path = export_json("m", ws)
    data = json.load(open(path, encoding="utf-8"))
    assert data["brand"] == "m"
    assert "Ruj" in data["pools"]
    assert data["tagged_count"] == 1


def test_export_excel_three_sheets_dynamic_columns(tmp_path):
    ws = _ws(tmp_path)
    path = export_excel("m", ws)
    wb = openpyxl.load_workbook(path)
    assert wb.sheetnames == ["Ürünler", "Havuz Özeti", "Kombinasyonlar"]
    urunler = wb["Ürünler"]
    headers = [c.value for c in urunler[1]]
    assert headers[:3] == ["Ürün Adı", "URL", "Kategori"]
    assert "Bitiş" in headers
    assert urunler.cell(row=2, column=headers.index("Bitiş") + 1).value == "Mat"


def test_supabase_sink_upserts(tmp_path):
    resp = MagicMock(status_code=201, text="")
    with patch("outputs.supabase_sink.requests.post", return_value=resp) as post:
        sink = SupabaseSink("https://x.supabase.co", "key")
        sink.upsert("pools", [{"brand_slug": "m", "category": "Ruj"}], conflict="brand_slug,category")
    url = post.call_args[0][0]
    assert url.endswith("/rest/v1/pools")
    assert post.call_args[1]["headers"]["apikey"] == "key"
```

- [ ] **Step 2: FAIL gör** — `python -m pytest tests/test_outputs.py -q`

- [ ] **Step 3: Implementasyon**

`outputs/json_sink.py`:
```python
"""Konsolide JSON dışa aktarımı: havuzlar + etiket sayısı + kombinasyonlar tek dosyada."""
import json
import os


def export_json(brand_slug: str, ws) -> str:
    pools = {}
    pools_dir = ws.path("pools")
    if os.path.isdir(pools_dir):
        for name in sorted(os.listdir(pools_dir)):
            if name.endswith(".json") and not name.startswith("_"):
                pools[name[:-5]] = ws.read_json(f"pools/{name}")
    data = {
        "brand": brand_slug,
        "pools": pools,
        "tagged_count": len(ws.read_jsonl("tagged/tagged.jsonl")),
        "combos": ws.read_json("combos/combos.json", default=[]),
    }
    out = ws.path("exports/export.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return out
```

`outputs/excel_sink.py`:
```python
"""Genel Excel şablonu: Ürünler (dinamik facet kolonları), Havuz Özeti, Kombinasyonlar."""
import os

import openpyxl
from openpyxl.styles import Font

from facets.pool_builder import pool_values


def export_excel(brand_slug: str, ws) -> str:
    tagged = ws.read_jsonl("tagged/tagged.jsonl")
    combos = ws.read_json("combos/combos.json", default=[])
    pools = {}
    pools_dir = ws.path("pools")
    if os.path.isdir(pools_dir):
        for name in sorted(os.listdir(pools_dir)):
            if name.endswith(".json") and not name.startswith("_"):
                pools[name[:-5]] = ws.read_json(f"pools/{name}")

    wb = openpyxl.Workbook()
    bold = Font(bold=True)

    sh = wb.active
    sh.title = "Ürünler"
    facet_cols = sorted({g for r in tagged for g in r.get("tags", {})})
    headers = ["Ürün Adı", "URL", "Kategori"] + facet_cols
    sh.append(headers)
    for c in sh[1]:
        c.font = bold
    for r in tagged:
        row = [r.get("name"), r.get("url"), r.get("category")]
        row += [r.get("tags", {}).get(g, {}).get("value", "") for g in facet_cols]
        sh.append(row)

    sh2 = wb.create_sheet("Havuz Özeti")
    sh2.append(["Kategori", "Grup", "Değer Sayısı", "Değerler"])
    for c in sh2[1]:
        c.font = bold
    for cat, pool in pools.items():
        for group, values in pool_values(pool).items():
            sh2.append([cat, group, len(values), ", ".join(values)])

    sh3 = wb.create_sheet("Kombinasyonlar")
    sh3.append(["Kombinasyon", "Aranma Hacmi", "Karar"])
    for c in sh3[1]:
        c.font = bold
    for c in combos:
        sh3.append([c.get("combo"), c.get("volume"), c.get("decision")])

    out = ws.path(f"exports/{brand_slug}.xlsx")
    wb.save(out)
    return out
```

`outputs/supabase_sink.py`:
```python
"""Supabase PostgREST sink: brand_slug ile çok kiracılı upsert. Şema: docs/supabase_schema.sql"""
import requests


class SupabaseSink:
    def __init__(self, url: str, service_key: str):
        self.url = url.rstrip("/")
        self.key = service_key

    def upsert(self, table: str, rows: list, conflict: str):
        if not rows:
            return
        resp = requests.post(
            f"{self.url}/rest/v1/{table}",
            params={"on_conflict": conflict},
            headers={
                "apikey": self.key,
                "Authorization": f"Bearer {self.key}",
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates",
            },
            json=rows,
            timeout=60,
        )
        if resp.status_code not in (200, 201, 204):
            raise RuntimeError(f"Supabase {table} upsert hatası {resp.status_code}: {resp.text[:300]}")


def export_supabase(brand_slug: str, ws, cfg: dict):
    sink = SupabaseSink(cfg["url"], cfg["service_key"])
    import os
    pools_dir = ws.path("pools")
    pool_rows = []
    if os.path.isdir(pools_dir):
        for name in sorted(os.listdir(pools_dir)):
            if name.endswith(".json") and not name.startswith("_"):
                pool_rows.append({"brand_slug": brand_slug, "category": name[:-5],
                                  "pool": ws.read_json(f"pools/{name}")})
    sink.upsert("pools", pool_rows, conflict="brand_slug,category")
    tag_rows = [{"brand_slug": brand_slug, "product_id": r["id"], "url": r.get("url"),
                 "name": r.get("name"), "category": r.get("category"), "tags": r.get("tags")}
                for r in ws.read_jsonl("tagged/tagged.jsonl")]
    sink.upsert("product_tags", tag_rows, conflict="brand_slug,product_id")
    combo_rows = [{"brand_slug": brand_slug, "combo": c["combo"], "volume": c.get("volume"),
                   "decision": c.get("decision"), "parts": c.get("parts")}
                  for c in ws.read_json("combos/combos.json", default=[])]
    sink.upsert("combos", combo_rows, conflict="brand_slug,combo")
```

- [ ] **Step 4: PASS** — `python -m pytest tests/test_outputs.py -q`

- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: çıktı sink'leri — JSON, genel Excel şablonu, Supabase upsert"`

---

### Task 17: review/ — HTML rapor + Streamlit onay ekranı

**Files:**
- Create: `review/html_report.py`, `review/streamlit_app.py`
- Test: `tests/test_review.py` (HTML için; Streamlit manuel doğrulanır)

- [ ] **Step 1: Failing test yaz**

`tests/test_review.py`:
```python
from core.state import Workspace
from facets.pool_builder import build_pool
from review.html_report import export_html_report


def test_html_report_contains_groups_and_values(tmp_path):
    ws = Workspace("m", root=str(tmp_path)).ensure()
    ws.write_json("pools/Ruj.json", build_pool("Ruj", [{"Bitiş": ["Mat", "Parlak"]}], None))
    path = export_html_report("Flormar", ws)
    html = open(path, encoding="utf-8").read()
    assert "Flormar" in html and "Ruj" in html and "Mat" in html and "Bitiş" in html
```

- [ ] **Step 2: FAIL gör** — `python -m pytest tests/test_review.py -q`

- [ ] **Step 3: Implementasyon**

`review/html_report.py`:
```python
"""Salt-okunur statik HTML havuz raporu — GitHub Pages/Vercel'de paylaşılabilir."""
import html as html_mod
import os

from facets.pool_builder import pool_values

TEMPLATE = """<!DOCTYPE html><html lang="tr"><head><meta charset="utf-8">
<title>{brand} — Facet Havuz Raporu</title>
<style>body{{font-family:system-ui;margin:2rem;max-width:960px}}h2{{border-bottom:2px solid #eee;padding-bottom:4px}}
table{{border-collapse:collapse;width:100%;margin-bottom:1.5rem}}td,th{{border:1px solid #ddd;padding:6px 10px;text-align:left;vertical-align:top}}
th{{background:#f7f7f7}}.count{{color:#888;font-size:0.85em}}</style></head><body>
<h1>{brand} — Facet Havuz Raporu</h1>{sections}</body></html>"""


def export_html_report(brand_name: str, ws) -> str:
    sections = []
    pools_dir = ws.path("pools")
    if os.path.isdir(pools_dir):
        for name in sorted(os.listdir(pools_dir)):
            if not name.endswith(".json") or name.startswith("_"):
                continue
            pool = ws.read_json(f"pools/{name}")
            rows = "".join(
                f"<tr><th>{html_mod.escape(g)} <span class='count'>({len(v)})</span></th>"
                f"<td>{html_mod.escape(', '.join(v))}</td></tr>"
                for g, v in pool_values(pool).items()
            )
            sections.append(f"<h2>{html_mod.escape(name[:-5])}</h2><table>{rows}</table>")
    out = ws.path("exports/report.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(TEMPLATE.format(brand=html_mod.escape(brand_name), sections="".join(sections)))
    return out
```

`review/streamlit_app.py`:
```python
"""Streamlit facet onay ekranı.

Çalıştırma: streamlit run review/streamlit_app.py
Lokal kullanım için hesap gerekmez. Online paylaşım: Streamlit Community Cloud
(GitHub hesabıyla giriş + repo bağlama yeterli).
"""
import os
import sys

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.state import Workspace
from facets.pool_builder import pool_values

st.set_page_config(page_title="Facet Onay", layout="wide")
st.title("Facet Havuz Onayı")

root = "workspace"
brands = sorted(d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d))) \
    if os.path.isdir(root) else []
if not brands:
    st.warning("workspace/ altında marka bulunamadı. Önce 'python run.py collect' çalıştırın.")
    st.stop()

brand = st.sidebar.selectbox("Marka", brands)
ws = Workspace(brand)
pool_files = sorted(f for f in os.listdir(ws.path("pools"))
                    if f.endswith(".json") and not f.startswith("_"))
if not pool_files:
    st.warning("Bu marka için havuz yok. Önce 'pools' aşamasını çalıştırın.")
    st.stop()

pool_file = st.sidebar.selectbox("Kategori havuzu", pool_files)
pool = ws.read_json(f"pools/{pool_file}")
st.subheader(pool.get("arama_kelimesi", pool_file))
if pool.get("reviewed"):
    st.success("Bu havuz onaylanmış.")

edited = {}
for group, values in pool_values(pool).items():
    keep = st.multiselect(f"{group} ({len(values)} değer)", values, default=values, key=group)
    if keep:
        edited[group] = keep

col1, col2 = st.columns(2)
if col1.button("Kaydet"):
    pool["gap_analizi"]["birlesik_filtre_havuzu"] = edited
    ws.write_json(f"pools/{pool_file}", pool)
    st.success("Kaydedildi.")
if col2.button("Kaydet ve Onayla"):
    pool["gap_analizi"]["birlesik_filtre_havuzu"] = edited
    pool["reviewed"] = True
    ws.write_json(f"pools/{pool_file}", pool)
    st.success("Onaylandı.")
```

- [ ] **Step 4: PASS + manuel duman testi**

```bash
python -m pytest tests/test_review.py -q
python -c "import ast; ast.parse(open('review/streamlit_app.py').read()); print('OK')"
```

- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: onay arayüzleri — statik HTML rapor + Streamlit ekranı"`

---

### Task 18: core/pipeline.py — aşama orkestrasyonu

**Files:**
- Create: `core/pipeline.py`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: Failing test yaz**

`tests/test_pipeline.py`:
```python
import pytest
from core.pipeline import run_stage, STAGES
from core.brand_profile import BrandProfile
from core.state import Workspace
from llm.bridge import MockBridge


def _brand():
    return BrandProfile(name="Marka", slug="m", sector="kozmetik")


def test_stages_order():
    assert STAGES == ["collect", "taxonomy", "pools", "review", "tag", "cross", "export"]


def test_unknown_stage_raises():
    with pytest.raises(ValueError, match="bilinmeyen aşama"):
        run_stage("yok", _brand(), {}, root="/tmp")


def test_pools_stage_builds_from_raw_sources(tmp_path):
    ws = Workspace("m", root=str(tmp_path)).ensure()
    ws.write_json("products/raw_facets.json", {"Ruj": [{"Bitiş": ["mat", "MAT"]}]})
    ws.write_json("pools/_taxonomy.json", {"groups": [{"group": "Bitiş"}]})
    bridge = MockBridge({"pool_quality": {"remove": {}, "merge": {}}})
    run_stage("pools", _brand(), {}, root=str(tmp_path), bridge=bridge)
    pool = ws.read_json("pools/Ruj.json")
    assert pool["gap_analizi"]["birlesik_filtre_havuzu"]["Bitiş"] == ["Mat"]


def test_cross_stage_writes_combos(tmp_path):
    ws = Workspace("m", root=str(tmp_path)).ensure()
    from facets.pool_builder import build_pool
    pool = build_pool("Ruj", [{"Bitiş": ["Mat"]}], None)
    pool["reviewed"] = True
    ws.write_json("pools/Ruj.json", pool)
    run_stage("cross", _brand(), {"seo": {"volume_threshold": 100}}, root=str(tmp_path))
    combos = ws.read_json("combos/combos.json")
    assert combos[0]["combo"] == "Mat Ruj"
    assert combos[0]["decision"] == "filtre"
```

- [ ] **Step 2: FAIL gör** — `python -m pytest tests/test_pipeline.py -q`

- [ ] **Step 3: Implementasyon**

`core/pipeline.py`:
```python
"""Aşama orkestrasyonu. Her aşama bağımsız; inline modda PendingLLMWork üst katmana taşar."""
import os

from .state import Workspace

STAGES = ["collect", "taxonomy", "pools", "review", "tag", "cross", "export"]


def _bridge(config, ws, override=None):
    if override is not None:
        return override
    from llm.bridge import get_bridge
    return get_bridge(config, workspace=ws)


def _iter_pools(ws, only_reviewed=False):
    pools_dir = ws.path("pools")
    if not os.path.isdir(pools_dir):
        return
    for name in sorted(os.listdir(pools_dir)):
        if name.endswith(".json") and not name.startswith("_"):
            pool = ws.read_json(f"pools/{name}")
            if only_reviewed and not pool.get("reviewed"):
                continue
            yield name[:-5], pool


def stage_collect(brand, config, ws, **opts):
    from sources.generic_scraper import collect_from_urls
    from sources.trendyol import fetch_aggregations
    sc = config.get("scraper", {})
    url_file = ws.path("input/urls.txt")
    urls = []
    if os.path.exists(url_file):
        with open(url_file, encoding="utf-8") as f:
            urls = [l.strip() for l in f if l.strip() and not l.startswith("#")]
    counts = collect_from_urls(urls, ws, delay=sc.get("delay_seconds", 1.0),
                               timeout=sc.get("timeout", 20)) if urls else {}
    raw = ws.read_json("products/raw_facets.json", default={})
    for ty_url in brand.trendyol_urls:
        aggs = fetch_aggregations(ty_url)
        if aggs:
            key = opts.get("category") or brand.name
            raw.setdefault(key, []).append(aggs)
    ws.write_json("products/raw_facets.json", raw)
    return counts


def stage_taxonomy(brand, config, ws, bridge=None, **opts):
    from facets.taxonomy import propose_taxonomy
    raw = ws.read_json("products/raw_facets.json", default={})
    raw_groups = sorted({g for maps in raw.values() for m in maps for g in m})
    for p in ws.read_jsonl("products/products.jsonl"):
        raw_groups.extend(p.get("attributes", {}).keys())
    result = propose_taxonomy(brand.sector, sorted(set(raw_groups)),
                              _bridge(config, ws, bridge))
    ws.write_json("pools/_taxonomy.json", result)
    return result


def stage_pools(brand, config, ws, bridge=None, **opts):
    from facets.pool_builder import build_pool
    from facets.quality_checker import check_pool
    taxonomy = ws.read_json("pools/_taxonomy.json", default=None)
    allowed = [g["group"] for g in taxonomy["groups"]] if taxonomy else None
    raw = ws.read_json("products/raw_facets.json", default={})
    by_category = dict(raw)
    for p in ws.read_jsonl("products/products.jsonl"):
        cat = p.get("category") or "Genel"
        attrs = {k: [v] for k, v in (p.get("attributes") or {}).items()}
        if attrs:
            by_category.setdefault(cat, []).append(attrs)
    b = _bridge(config, ws, bridge)
    for category, source_maps in by_category.items():
        pool = build_pool(category, source_maps, allowed_groups=allowed)
        pool = check_pool(category, pool, b)
        ws.write_json(f"pools/{category}.json", pool)
    return list(by_category)


def stage_review(brand, config, ws, **opts):
    from review.html_report import export_html_report
    path = export_html_report(brand.name, ws)
    return {"html_report": path,
            "not": "Onay: sohbet içinde, streamlit run review/streamlit_app.py ile "
                   "veya HTML raporu paylaşarak. Onaylanan havuza reviewed=true yazılmalı."}


def stage_tag(brand, config, ws, bridge=None, **opts):
    from tagger.batch import tag_products
    pools = {cat: pool for cat, pool in _iter_pools(ws)}
    batch_size = config.get("llm", {}).get("batch_size", 50)
    return tag_products(ws, pools, _bridge(config, ws, bridge), batch_size=batch_size)


def stage_cross(brand, config, ws, **opts):
    from seo.cross_join import generate_combos
    from seo.volume import (apply_threshold, export_manual_csv,
                            fetch_volumes_dataforseo, import_volumes_csv)
    seo_cfg = config.get("seo", {})
    combos = []
    for category, pool in _iter_pools(ws, only_reviewed=True):
        combos.extend(generate_combos(category, pool,
                                      exclude_groups=seo_cfg.get("exclude_groups"),
                                      two_facet_pairs=seo_cfg.get("two_facet_pairs")))
    dfs = config.get("dataforseo", {})
    manual_csv = ws.path("input/volumes.csv")
    if opts.get("import_volumes"):
        volumes = import_volumes_csv(opts["import_volumes"])
    elif dfs.get("login") and dfs.get("password"):
        volumes = fetch_volumes_dataforseo([c["combo"] for c in combos],
                                           dfs["login"], dfs["password"])
    elif os.path.exists(manual_csv):
        volumes = import_volumes_csv(manual_csv)
    else:
        export_manual_csv(combos, manual_csv)
        volumes = {}
    ws.write_json("combos/combos.json",
                  apply_threshold(combos, volumes, seo_cfg.get("volume_threshold", 100)))
    return len(combos)


def stage_export(brand, config, ws, **opts):
    from outputs.json_sink import export_json
    out = {"json": export_json(brand.slug, ws)}
    targets = opts.get("targets") or ["excel"]
    if "excel" in targets:
        from outputs.excel_sink import export_excel
        out["excel"] = export_excel(brand.slug, ws)
    if "supabase" in targets:
        sb = config.get("supabase", {})
        if sb.get("url") and sb.get("service_key"):
            from outputs.supabase_sink import export_supabase
            export_supabase(brand.slug, ws, sb)
            out["supabase"] = "yazıldı"
        else:
            out["supabase"] = "atlandı — config.json'da supabase.url/service_key boş"
    return out


_HANDLERS = {
    "collect": stage_collect, "taxonomy": stage_taxonomy, "pools": stage_pools,
    "review": stage_review, "tag": stage_tag, "cross": stage_cross, "export": stage_export,
}


def run_stage(stage: str, brand, config: dict, root: str = "workspace",
              bridge=None, **opts):
    if stage not in _HANDLERS:
        raise ValueError(f"bilinmeyen aşama: {stage} (geçerli: {', '.join(STAGES)})")
    ws = Workspace(brand.slug, root=root).ensure()
    ws.write_json("_stage.json", {"stage": stage})
    kwargs = dict(opts)
    if stage in ("taxonomy", "pools", "tag"):
        kwargs["bridge"] = bridge
    return _HANDLERS[stage](brand, config, ws, **kwargs)
```

- [ ] **Step 4: PASS** — `python -m pytest tests/test_pipeline.py -q`

- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: pipeline orkestrasyonu — 7 çalıştırılabilir aşama"`

---

### Task 19: run.py — CLI

**Files:**
- Create: `run.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Failing test yaz**

`tests/test_cli.py`:
```python
import json
import subprocess
import sys


def _run(*args):
    return subprocess.run([sys.executable, "run.py", *args], capture_output=True, text=True)


def test_help_lists_stages():
    out = _run("--help")
    assert out.returncode == 0
    for cmd in ("init", "collect", "pools", "tag", "cross", "export", "continue"):
        assert cmd in out.stdout


def test_stage_without_brand_fails_clearly():
    out = _run("collect")
    assert out.returncode != 0
```

- [ ] **Step 2: FAIL gör** — `python -m pytest tests/test_cli.py -q`

- [ ] **Step 3: Implementasyon**

`run.py`:
```python
"""category-product-tag-builder — herhangi bir marka için kategori & facet üretimi.

KULLANIM:
    python run.py init                              # marka profili sihirbazı
    python run.py collect --brand flormar           # veri toplama (input/urls.txt + Trendyol)
    python run.py taxonomy --brand flormar          # sektöre göre facet grubu önerisi
    python run.py pools --brand flormar             # havuz üretimi + kalite denetimi
    python run.py review --brand flormar            # HTML rapor üret + onay yönergesi
    python run.py tag --brand flormar               # ürünleri etiketle
    python run.py cross --brand flormar             # kombinasyon + hacim + eşik
    python run.py cross --brand flormar --import-volumes input/volumes.csv
    python run.py export --brand flormar --targets excel supabase
    python run.py continue --brand flormar          # son aşamayı kaldığı yerden sürdür
    python run.py retry-errors --brand flormar      # hatalı collect URL'lerini yeniden dene

LLM provider config.json'da seçilir (inline | claude-cli | anthropic | gemini | perplexity).
inline modda komut, LLM sonucu bekleyen görev dosyalarını listeleyip çıkar (exit 2);
sohbetteki Claude sonuçları yazınca aynı komut yeniden çalıştırılır.
"""
import argparse
import json
import os
import sys

from core.brand_profile import BrandProfile, load_brand
from core.pipeline import STAGES, run_stage
from core.state import Workspace
from llm.bridge import PendingLLMWork


def load_config() -> dict:
    if os.path.exists("config.json"):
        with open("config.json", encoding="utf-8") as f:
            return json.load(f)
    return {"llm": {"provider": "inline"}}


def cmd_init(args):
    print("Yeni marka profili:")
    data = {
        "name": input("  Marka adı: ").strip(),
        "slug": input("  Slug (küçük harf, tire): ").strip(),
        "sector": input("  Sektör (moda/kozmetik/banyo/...): ").strip(),
        "site_domain": input("  Site domain [boş geçilebilir]: ").strip(),
        "trendyol_brand": input("  Trendyol marka adı [boş]: ").strip(),
        "language": input("  Dil [tr]: ").strip() or "tr",
    }
    urls = input("  Trendyol kategori/marka URL'leri (virgülle) [boş]: ").strip()
    data["trendyol_urls"] = [u.strip() for u in urls.split(",") if u.strip()]
    os.makedirs("brands", exist_ok=True)
    path = os.path.join("brands", f"{data['slug']}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    load_brand(data["slug"])
    print(f"✓ {path} oluşturuldu. Sonraki adım: workspace/{data['slug']}/input/urls.txt "
          f"dosyasına ürün URL'lerini koyup 'python run.py collect --brand {data['slug']}'")


def cmd_retry_errors(args):
    brand = load_brand(args.brand)
    ws = Workspace(brand.slug).ensure()
    errors = [e for e in ws.read_jsonl("errors.jsonl") if e.get("stage") == "collect"]
    if not errors:
        print("collect hatası yok.")
        return
    from sources.generic_scraper import collect_from_urls
    urls = [e["url"] for e in errors if e.get("url")]
    print(f"{len(urls)} hatalı URL yeniden deneniyor...")
    counts = collect_from_urls(urls, ws)
    print(f"✓ yeni: {counts['yeni']}, hata: {counts['hata']}")


def main():
    parser = argparse.ArgumentParser(
        prog="run.py", description="Marka bağımsız kategori & facet üretim aracı",
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init", help="marka profili sihirbazı")
    for stage in STAGES + ["continue"]:
        p = sub.add_parser(stage, help=f"'{stage}' aşamasını çalıştır")
        p.add_argument("--brand", required=True)
        if stage == "cross":
            p.add_argument("--import-volumes", dest="import_volumes")
        if stage == "export":
            p.add_argument("--targets", nargs="+", default=["excel"],
                           choices=["excel", "supabase", "json"])
        if stage == "collect":
            p.add_argument("--category", help="Trendyol facet'lerinin yazılacağı kategori adı")
    p_retry = sub.add_parser("retry-errors", help="hatalı collect URL'lerini yeniden dene")
    p_retry.add_argument("--brand", required=True)

    args = parser.parse_args()
    if args.cmd == "init":
        return cmd_init(args)
    if args.cmd == "retry-errors":
        return cmd_retry_errors(args)

    brand = load_brand(args.brand)
    config = load_config()
    stage = args.cmd
    if stage == "continue":
        ws = Workspace(brand.slug)
        state = ws.read_json("_stage.json", default=None)
        if not state:
            print("Sürdürülecek aşama yok."); return
        stage = state["stage"]
        print(f"Sürdürülüyor: {stage}")
    opts = {k: v for k, v in vars(args).items() if k not in ("cmd", "brand")}
    try:
        result = run_stage(stage, brand, config, **opts)
        print(f"✓ {stage} tamamlandı: {result}")
    except PendingLLMWork as e:
        print(str(e))
        print(f"\nSonuçlar yazıldıktan sonra: python run.py {stage} --brand {brand.slug}")
        sys.exit(2)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: PASS** — `python -m pytest tests/test_cli.py -q && python -m pytest tests/ -q`

- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: CLI — aşama komutları, init sihirbazı, continue/retry"`

---

### Task 20: .claude/skills/tag-builder/SKILL.md

**Files:**
- Create: `.claude/skills/tag-builder/SKILL.md`

- [ ] **Step 1: SKILL.md yaz**

```markdown
---
name: tag-builder
description: >
  Herhangi bir marka için kategori & facet üretimi: veri toplama, facet havuzu,
  ürün etiketleme, SEO kombinasyon + hacim, Excel/Supabase çıktısı. Kullanıcı bir
  marka adı verip kategori/facet/etiketleme isterse, "facet havuzu", "kategori üret",
  "ürün etiketle", "tag builder" derse bu skill'i kullan. LLM işlerini (taksonomi,
  kalite denetimi, etiketleme) pending_llm dosyaları üzerinden BİZZAT sen yaparsın —
  API anahtarı gerekmez.
---

# Tag Builder

Pipeline: collect → taxonomy → pools → review → tag → cross → export
Her aşama: `python run.py <aşama> --brand <slug>` (repo kökünden, .venv aktifken).

## Akış

1. **Profil yoksa**: kullanıcıya marka adı/sektör/Trendyol URL'lerini sor,
   `brands/<slug>.json` dosyasını kendin yaz (şablon: `brands/_template.json`).
2. **Ürün URL'leri**: kullanıcıdan al, `workspace/<slug>/input/urls.txt`'e yaz.
3. Aşamaları sırayla çalıştır. Komut **exit 2** ile çıkar ve pending_llm dosyaları
   listelerse → aşağıdaki "LLM görevi işleme" bölümünü uygula, komutu tekrar çalıştır.

## LLM görevi işleme (inline mod — SEN YAPARSIN)

1. Listelenen her `workspace/<slug>/pending_llm/<id>.json` dosyasını oku.
2. `prompt` alanındaki görevi uygula. Cevabın `schema` alanına uymalı
   (ör. `{"groups": "list"}` → sonuçta "groups" anahtarı liste olmalı).
3. Sonucu SAF JSON olarak `pending_llm/<id>.result.json` dosyasına Write ile yaz.
4. Tüm görevler bitince aynı run.py komutunu yeniden çalıştır.

## Onay (review aşaması)

Havuzları sohbette özet tablo olarak göster (grup → değer sayısı → ilk değerler).
Kullanıcının "sil/birleştir/ekle" taleplerini havuz JSON'una uygula
(`workspace/<slug>/pools/<Kategori>.json`). Onay gelince dosyaya `"reviewed": true`
ekle. Alternatifler: `streamlit run review/streamlit_app.py` veya
`exports/report.html` paylaşımı.

## Hacim (cross aşaması)

DataForSEO anahtarı yoksa komut `input/volumes.csv` üretir. Kullanıcı isterse
hacimleri sen web aramasıyla TAHMİN ETME — kullanıcıdan doldurmasını iste veya
DataForSEO MCP bağlıysa oradan çek, CSV'ye yaz, komutu tekrar çalıştır.

## Çıktı

`python run.py export --brand <slug> --targets excel supabase`
Excel her zaman güvenli seçenek; Supabase için config.json'da url+service_key olmalı
(şema: docs/supabase_schema.sql).
```

- [ ] **Step 2: Doğrula** — `python -c "import yaml,sys" 2>/dev/null || true` yerine basit kontrol: dosyanın frontmatter ile başladığını ve `---` ile kapandığını gözle doğrula.

- [ ] **Step 3: Commit** — `git add -A && git commit -m "feat: tag-builder skill — inline LLM akışı ve sohbet onay protokolü"`

---

### Task 21: docs/supabase_schema.sql + README.md

**Files:**
- Create: `docs/supabase_schema.sql`, `README.md`

- [ ] **Step 1: Şema dosyası**

`docs/supabase_schema.sql`:
```sql
-- category-product-tag-builder Supabase şeması (çok kiracılı: brand_slug)
create table if not exists pools (
  brand_slug text not null,
  category   text not null,
  pool       jsonb not null,
  updated_at timestamptz default now(),
  primary key (brand_slug, category)
);

create table if not exists product_tags (
  brand_slug text not null,
  product_id text not null,
  url        text,
  name       text,
  category   text,
  tags       jsonb,
  updated_at timestamptz default now(),
  primary key (brand_slug, product_id)
);

create table if not exists combos (
  brand_slug text not null,
  combo      text not null,
  volume     integer,
  decision   text,
  parts      jsonb,
  updated_at timestamptz default now(),
  primary key (brand_slug, combo)
);
```

- [ ] **Step 2: README.md**

İçerik (tam metin yazılır, özet değil): proje amacı (1 paragraf), kurulum (`python3 -m venv .venv && pip install -r requirements.txt && cp config.example.json config.json`), hızlı başlangıç (init → urls.txt → collect → taxonomy → pools → review → tag → cross → export komut blokları), LLM provider tablosu (5 satır: inline/claude-cli/anthropic/gemini/perplexity — gereksinimleriyle), çıktı seçenekleri (Excel/Supabase/JSON), Claude Code & claude.ai/code kullanımı ("repoyu açıp 'flormar için facet havuzu üret' demek yeterli — tag-builder skill'i akışı yönetir"), Streamlit onay ekranı bölümü (lokal hesap gerekmez; Community Cloud için GitHub girişi), spec ve plan dokümanlarına bağlantılar.

- [ ] **Step 3: Commit** — `git add -A && git commit -m "docs: README, Supabase şeması"`

---

### Task 22: Uçtan uca duman testi + push

**Files:**
- Create: `tests/test_e2e.py`

- [ ] **Step 1: E2E test yaz (ağsız, MockBridge ile tüm pipeline)**

`tests/test_e2e.py`:
```python
"""Uçtan uca: raw veri → taxonomy → pools → tag → cross → export (ağsız, mock LLM)."""
import openpyxl
from core.brand_profile import BrandProfile
from core.pipeline import run_stage
from core.state import Workspace
from llm.bridge import MockBridge


def test_full_pipeline(tmp_path):
    brand = BrandProfile(name="Flormar", slug="flormar", sector="kozmetik")
    ws = Workspace("flormar", root=str(tmp_path)).ensure()
    ws.append_jsonl("products/products.jsonl",
                    {"id": "p1", "url": "https://x/1", "name": "Mat Ruj Kiremit",
                     "category": "Ruj", "description": "", "attributes": {"Bitiş": "Mat"}})
    ws.write_json("products/raw_facets.json",
                  {"Ruj": [{"Bitiş": ["Mat", "Parlak"], "Ton": ["Kiremit", "Nude"]}]})
    bridge = MockBridge({
        "taxonomy_proposal": {"groups": [{"group": "Bitiş"}, {"group": "Ton"}]},
        "pool_quality": {"remove": {}, "merge": {}},
        "product_tagging": {"products": [{"id": "p1", "tags": {"Ton": "Kiremit"}}]},
    })
    run_stage("taxonomy", brand, {}, root=str(tmp_path), bridge=bridge)
    run_stage("pools", brand, {}, root=str(tmp_path), bridge=bridge)
    for name in ("Ruj",):
        pool = ws.read_json(f"pools/{name}.json")
        pool["reviewed"] = True
        ws.write_json(f"pools/{name}.json", pool)
    assert run_stage("tag", brand, {}, root=str(tmp_path), bridge=bridge) == 1
    run_stage("cross", brand, {"seo": {"volume_threshold": 100}}, root=str(tmp_path))
    out = run_stage("export", brand, {}, root=str(tmp_path), targets=["excel"])
    wb = openpyxl.load_workbook(out["excel"])
    assert wb["Ürünler"].max_row == 2
    assert wb["Kombinasyonlar"].max_row >= 2
```

- [ ] **Step 2: Tüm test takımı yeşil** — `python -m pytest tests/ -q` → tamamı PASS

- [ ] **Step 3: Push**

```bash
git add -A && git commit -m "test: uçtan uca pipeline duman testi" && git push origin main
```

- [ ] **Step 4: Canlı doğrulama (opsiyonel ama önerilir)**

Gerçek bir Trendyol URL'siyle aggregation testi:
```bash
source .venv/bin/activate && python -c "
from sources.trendyol import fetch_aggregations
out = fetch_aggregations('https://www.trendyol.com/abiye-x-c56')
print(list(out.items())[:3] if out else 'Cloudflare engeli — beklenen risk, akış kırılmaz')"
```

---

## Self-Review Notları (plan yazarı tarafından dolduruldu)

- **Spec kapsama:** Spec §3 mimari → Task 1–21; §4 sekiz aşama → init Task 19 (sihirbaz), collect/taxonomy/pools/review/tag/cross/export Task 18; §5 LLM köprüsü → Task 5–8; §6 çıktılar → Task 16; §7 hata yönetimi → errors.jsonl (Task 9, 14), retry-errors (Task 19), PendingLLMWork (Task 7); §8 test → her taskte TDD + Task 22 E2E; §9 taşıma haritası → Task 4 (normalizer birebir), Task 10 (Trendyol), Task 13 ve 16 (slim yeniden yazım — spec'teki "uyarlanır" notuna uygun).
- **Bilinçli sapmalar:** (1) Üç API istemcisi tek `api_clients.py` dosyasında (DRY). (2) `quality_checker` ve `supabase_sink` taşıma yerine slim yeniden yazım — spec §9'daki uyarlama notlarıyla uyumlu. (3) `json_sink` workspace verilerini konsolide eder; ham JSONL'ler zaten her zaman yazılıyor.
- **Tip tutarlılığı:** `pool_values()` Task 12'de tanımlanır, Task 13/14/15/16/17'de aynı imzayla kullanılır. `Workspace` arayüzü Task 3'te sabitlenir. `new_task/validate_result/extract_json` Task 5'te sabitlenir.
