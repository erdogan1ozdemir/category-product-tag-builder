"""Trendyol kaynak adaptörü.

Aggregation kodu v5 pool_creator/scripts/trendyol_seo_landing_enricher.py'den
uyarlandı (fetch_landing_aggregation). SEO landing ayıklama fonksiyonları aynı
dosyadan birebir kopyalandı.
"""
import json
import re
import unicodedata
from html import unescape
from typing import Dict, List, Optional, Tuple
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


# ── v5'ten birebir taşınan SEO landing fonksiyonları ──

SEO_USER_AGENTS = (
    "Mozilla/5.0",
    (
        "Mozilla/5.0 (compatible; Googlebot/2.1; "
        "+http://www.google.com/bot.html)"
    ),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
)

DROP_LANDING_LABEL_TOKENS = {
    "airfryer",
    "apple",
    "ipad",
    "razer",
    "dyson",
    "tv",
    "telefon",
    "laptop",
    "tablet",
}


def _slug_text(value: str) -> str:
    if not value:
        return ""
    value = value.lower()
    value = (
        value.replace("ı", "i")
        .replace("ğ", "g")
        .replace("ü", "u")
        .replace("ş", "s")
        .replace("ö", "o")
        .replace("ç", "c")
    )
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def _json_from_script_assignment(html: str, prop_name: str) -> Optional[dict]:
    marker = f'window["__{prop_name}__PROPS"]='
    start = html.find(marker)
    if start < 0:
        return None
    json_start = start + len(marker)
    end = html.find("</script>", json_start)
    if end < 0:
        return None
    raw = html[json_start:end].strip()
    try:
        return json.loads(raw)
    except Exception:
        return None


def _walk_landing_items(obj, source: str, section: str = "") -> List[dict]:
    items = []
    if isinstance(obj, dict):
        current_section = section
        if isinstance(obj.get("elements"), list) and obj.get("title"):
            current_section = str(obj.get("title"))

        path = obj.get("path")
        label = obj.get("displayName") or obj.get("text")
        if path and label and re.search(r"-y-s\d+", str(path)):
            full_url = str(path)
            if full_url.startswith("/"):
                full_url = TRENDYOL_BASE + full_url
            items.append({
                "label": str(label).strip(),
                "url": full_url,
                "path": str(path),
                "source": source,
                "section": current_section,
            })

        for value in obj.values():
            items.extend(_walk_landing_items(value, source, current_section))
    elif isinstance(obj, list):
        for value in obj:
            items.extend(_walk_landing_items(value, source, section))
    return items


def _is_relevant_landing(item: dict, category: str) -> bool:
    label_slug = _slug_text(item.get("label", ""))
    url_slug = _slug_text(item.get("url", ""))
    category_slug = _slug_text(category)
    if not label_slug or not category_slug:
        return False
    tokens = set(label_slug.split("-")) | set(url_slug.split("-"))
    if tokens & DROP_LANDING_LABEL_TOKENS:
        return False
    category_tokens = [t for t in category_slug.split("-") if t]
    if not category_tokens:
        return False
    return any(token in tokens for token in category_tokens)


def _fetch_html(url: str, timeout: int = 20) -> Optional[str]:
    for user_agent in SEO_USER_AGENTS:
        headers = {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
        }
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
        except Exception:
            continue
        if resp.status_code != 200:
            continue
        html = resp.text
        if "__bic-seo__PROPS" in html or "__internal-linking-seo__PROPS" in html:
            return html
        if html:
            fallback_html = html
    return locals().get("fallback_html")


def extract_category_seo_landings(category_url: str, category: str) -> List[dict]:
    html = _fetch_html(category_url)
    if not html:
        return []

    items = []
    for prop_name in ("bic-seo", "internal-linking-seo"):
        data = _json_from_script_assignment(html, prop_name)
        if data:
            items.extend(_walk_landing_items(data, prop_name))

    seen = set()
    out = []
    for item in items:
        url = item.get("url")
        if not url or url in seen:
            continue
        if not _is_relevant_landing(item, category):
            continue
        match = re.search(r"-y-s(\d+)", url)
        item["landing_id"] = match.group(1) if match else ""
        item["slug"] = url.rstrip("/").split("/")[-1]
        seen.add(url)
        out.append(item)
    return out
