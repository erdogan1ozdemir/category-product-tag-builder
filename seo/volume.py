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
