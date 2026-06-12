"""URL listesinden genel ürün ayıklama. Öncelik: JSON-LD > OpenGraph > sezgisel HTML."""
import json
import re
import time
from html import unescape

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
        if isinstance(brand, list):
            brand = brand[0] if brand else None
            if isinstance(brand, dict):
                brand = brand.get("name")
        if brand is not None and not isinstance(brand, str):
            brand = str(brand)
        offers = obj.get("offers") or {}
        if isinstance(offers, list):
            offers = offers[0] if offers else {}
        if not isinstance(offers, dict):
            offers = {}
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
    return unescape(m.group(1).strip()) if m else None


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
        name = unescape(re.sub(r"<[^>]+>", " ", h1.group(1)).strip())
    elif title:
        name = unescape(title.group(1).split("|")[0].strip())
    attrs = {}
    for row in re.finditer(r"<tr[^>]*>\s*<t[hd][^>]*>(.*?)</t[hd]>\s*<td[^>]*>(.*?)</td>", html, re.S | re.I):
        key = unescape(re.sub(r"<[^>]+>", "", row.group(1)).strip())
        val = unescape(re.sub(r"<[^>]+>", "", row.group(2)).strip())
        if key and val:
            attrs[key] = val
    for pair in re.finditer(r"<dt[^>]*>(.*?)</dt>\s*<dd[^>]*>(.*?)</dd>", html, re.S | re.I):
        key = unescape(re.sub(r"<[^>]+>", "", pair.group(1)).strip())
        val = unescape(re.sub(r"<[^>]+>", "", pair.group(2)).strip())
        if key and val:
            attrs[key] = val
    return {"name": name, "description": None, "images": [], "price": None, "attributes": attrs}


def scrape_product(url: str, html: str = None, timeout: int = 20) -> dict:
    html = html if html is not None else fetch_html(url, timeout=timeout)
    layers = []
    for parser in (parse_heuristic, parse_opengraph, parse_jsonld):
        try:
            layers.append(parser(html))
        except Exception:
            layers.append(None)
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
        pid = product_record(url)["id"]
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
