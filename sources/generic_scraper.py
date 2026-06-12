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


def _last_segment(value: str) -> str:
    """'Kozmetik > Makyaj > Ruj' veya 'Kozmetik/Makyaj/Ruj' → 'Ruj'"""
    for sep in (">", "/"):
        if sep in value:
            return value.split(sep)[-1].strip()
    return value.strip()


def parse_jsonld(html: str):
    product_result = None
    breadcrumb_category = None

    for obj in _iter_jsonld_objects(html):
        typ = str(obj.get("@type", "")).lower()

        if typ == "product" and product_result is None:
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
            # Extract category from Product object
            raw_cat = obj.get("category")
            category = None
            if isinstance(raw_cat, str) and raw_cat.strip():
                category = _last_segment(raw_cat)
            product_result = {
                "name": obj.get("name"),
                "description": obj.get("description"),
                "brand": brand,
                "images": images,
                "price": str(offers.get("price")) if offers.get("price") is not None else None,
                "attributes": attrs,
                "category": category,
            }

        elif typ == "breadcrumblist" and breadcrumb_category is None:
            items = obj.get("itemListElement") or []
            if items:
                last = items[-1]
                if isinstance(last, dict):
                    item_node = last.get("item") or {}
                    name = (
                        item_node.get("name") if isinstance(item_node, dict) else None
                    ) or last.get("name")
                    if name:
                        breadcrumb_category = str(name).strip()

    if product_result is not None:
        # Breadcrumb fills only when product has no category
        if not product_result.get("category") and breadcrumb_category:
            product_result["category"] = breadcrumb_category
        return product_result
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
    # Tailwind-tarzı div-grid spec satırları: <div><div class="...font-semibold...">Etiket</div><div>Değer</div></div>
    for pair in re.finditer(
        r"<div[^>]*>\s*<div[^>]*font-(?:semibold|bold)[^>]*>(.*?)</div>\s*<div[^>]*>(.*?)</div>\s*</div>",
        html, re.S | re.I,
    ):
        key = unescape(re.sub(r"<[^>]+>", "", pair.group(1)).strip())
        val = unescape(re.sub(r"<[^>]+>", "", pair.group(2)).strip())
        if key and val and len(key) <= 60 and len(val) <= 120:
            attrs.setdefault(key, val)
    return {"name": name, "description": None, "images": [], "price": None, "attributes": attrs}


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
            page = browser.new_page(user_agent=HEADERS["User-Agent"], locale="tr-TR")
            page.goto(url, timeout=timeout * 1000, wait_until="domcontentloaded")
            try:
                page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass
            html = page.content()
        finally:
            browser.close()
    return html


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


def collect_from_urls(
    urls: list,
    workspace,
    delay: float = 1.0,
    timeout: int = 20,
    render_fallback: bool = True,
    categories: dict | None = None,
) -> dict:
    """URL listesini gez; işlenmişleri atla; hataları errors.jsonl'a yaz.

    render_fallback=True ise statik fetch'te ürün adı alınamazsa
    Playwright ile yeniden dener.

    categories: url → explicit category mapping (kazınan değerin üzerine yazar).
    """
    done = workspace.processed_ids("products/products.jsonl")
    counts = {"yeni": 0, "atlandı": 0, "hata": 0, "render": 0}
    if categories is None:
        categories = {}
    for url in urls:
        pid = product_record(url)["id"]
        if pid in done:
            counts["atlandı"] += 1
            continue
        render_denendi = False
        rec = None
        error = None
        try:
            rec = scrape_product(url, timeout=timeout)
        except Exception as e:
            error = e
            rec = None

        # Static başarısız ya da isim yoksa render fallback dene
        if (rec is None or not rec.get("name")) and render_fallback:
            render_denendi = True
            try:
                rendered_html = fetch_html_rendered(url, timeout=max(timeout, 30))
                rec = scrape_product(url, html=rendered_html)
                if rec.get("name"):
                    if url in categories:
                        rec["category"] = categories[url]
                    workspace.append_jsonl("products/products.jsonl", rec)
                    counts["yeni"] += 1
                    counts["render"] += 1
                    error = None  # başarılı, hata kaydetme
                else:
                    error = error or ValueError("ürün adı ayıklanamadı (render sonrası)")
            except Exception as e:
                error = e
                rec = None
        elif rec is not None and rec.get("name"):
            if url in categories:
                rec["category"] = categories[url]
            workspace.append_jsonl("products/products.jsonl", rec)
            counts["yeni"] += 1
            error = None

        if error is not None or (rec is not None and not rec.get("name") and not render_denendi):
            # Son kontrol: hata kaydet
            if error is None:
                error = ValueError("ürün adı ayıklanamadı")
            workspace.append_jsonl(
                "errors.jsonl",
                {
                    "stage": "collect",
                    "url": url,
                    "error": str(error),
                    "render_denendi": render_denendi,
                },
            )
            counts["hata"] += 1

        time.sleep(delay)
    return counts
