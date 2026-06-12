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
