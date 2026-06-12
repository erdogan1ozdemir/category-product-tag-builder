"""Sektöre uygun facet (filtre) grubu taksonomisi önerisi — LLM görevi."""
from llm.bridge import LLMError, run_validated
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
        raise LLMError(f"Taksonomi önerisi doğrulanamadı (görev {failed[0][0]['id']}): {failed[0][1]}")
    return ok[task["id"]]
