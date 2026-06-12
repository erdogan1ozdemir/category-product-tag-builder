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
    if data["slug"] != slug:
        raise ValueError(
            f"Dosya adı ile slug eşleşmiyor: {slug}.json içinde slug='{data['slug']}'"
        )
    known = {f.name for f in fields(BrandProfile)}
    return BrandProfile(**{k: v for k, v in data.items() if k in known})
