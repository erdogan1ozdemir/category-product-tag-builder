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
