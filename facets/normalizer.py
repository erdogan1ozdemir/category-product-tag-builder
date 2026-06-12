"""
normalization/normalizer.py

Facet havuzunu normalize eden fonksiyonlar.

Dış dünyaya açılan arayüz:
    normalize_value_list(raw_list, group_name=None) -> List[str]
"""
# Kaynak: Category-generator-v5/product_tagger/normalization/normalizer.py (birebir taşındı)

import re
import unicodedata


# ==========================================
# TÜRKÇE YARDIMCILAR
# ==========================================
def tr_lower(text):
    return text.replace("İ", "i").replace("I", "ı").lower()


def tr_title(text):
    if not text:
        return ""
    text = tr_lower(text)

    def upper_tr(ch):
        if ch == "i":
            return "İ"
        if ch == "ı":
            return "I"
        return ch.upper()

    def cap_match(match):
        prefix, first = match.groups()
        return prefix + upper_tr(first)

    return re.sub(r"(^|[\s/+\-&(])([a-zçğıöşü])", cap_match, text)


def clean_filter_value(val):
    if not val:
        return ""
    val = unicodedata.normalize("NFKC", str(val))
    val = re.sub(r"<[^>]+>", "", val)
    val = re.sub(r"[\x00-\x1f\x7f\xa0​-‏‪-‮]", "", val)
    return " ".join(val.split())


# ==========================================
# HARDCODED MİNİMAL JUNK LİSTESİ
# ==========================================
_JUNK_VALUES = frozenset({
    "belirtilmemiş", "belirtilmemis", "bilinmiyor", "diğer", "diger",
    "diğerleri", "digerleri", "other", "yok", "mix", "n/a", "nope",
    "genel", "çeşitli", "cesitli", "gore", "tek ebat", "ip", "ıp",
    "ek özellik mevcut değil", "tek kişilik", "standart",
})

# Beden boyut kısaltmaları için regex — "2xl" → "2XL", "xl" → "XL", "2xl-3xl" → "2XL-3XL"
_SIZE_UNIT = r"\d*(?:xs|s|m|l|xl|xxl|\d+xl)"
_SIZE_RE = re.compile(rf"^(\d*)(xs|s|m|l|xl|xxl|\d+xl)$", re.IGNORECASE)
_SIZE_RANGE_RE = re.compile(rf"^({_SIZE_UNIT})-({_SIZE_UNIT})$", re.IGNORECASE)

# Özdilek ham beden formatları: "10yas" → "10 Yaş", "6/7yas" → "6-7 Yaş", "0/12ay" → "0-12 Ay"
_BEDEN_AGE_RE = re.compile(r"^(\d+(?:[,\.]\d+)?)\s*ya[şs]$", re.IGNORECASE)
_BEDEN_AGE_RANGE_RE = re.compile(r"^(\d+)[/\-](\d+)\s*ya[şs]$", re.IGNORECASE)
_BEDEN_MONTH_RANGE_RE = re.compile(r"^(\d+)[/\-](\d+)\s*ay$", re.IGNORECASE)

_NUMERIC_CM_REGEX = re.compile(r"^\d+\s*cm$", re.IGNORECASE)
_ONLY_PUNCTUATION_REGEX = re.compile(r"^[\W_]+$")
_ONLY_DIGITS_REGEX = re.compile(r"^\d[\d.,\s]+$")
_SHOE_FRACTION_RE = re.compile(r"^\d+\s+\d/\d$")

_GROUP_ALIASES = {
    "Materyal": {
        "organik pamuk": "Pamuk",
        "pamuklu": "Pamuk",
    },
}


def is_junk(val_lower, group_name=None):
    if val_lower in _JUNK_VALUES:
        return True
    if group_name == "Beden" and _SIZE_RE.match(val_lower):
        return False
    if val_lower.isdigit():
        return True
    if len(val_lower) < 2:
        return True
    if _NUMERIC_CM_REGEX.match(val_lower):
        return True
    if _ONLY_PUNCTUATION_REGEX.match(val_lower):
        return True
    if _ONLY_DIGITS_REGEX.match(val_lower):
        return True
    if _SHOE_FRACTION_RE.match(val_lower):
        return True
    return False


# ==========================================
# SPLIT
# ==========================================
# Tire (-) kasıtlı olarak dahil edilmedi: "Slim-Fit", "A-form" gibi
# değerleri yanlış bölmemek için.
COMPOSITE_SPLIT_REGEX = re.compile(
    r"\s*[/+&]\s*|\s*,\s*|\s+ve\s+", re.IGNORECASE
)

_NUMERIC_FRACTION_REGEX = re.compile(r"\d\s*[/\-]\s*\d")
_LEADS_WITH_NUMBER_REGEX = re.compile(r"^\s*\d")
_PERCENT_PART_REGEX = re.compile(
    r"%\s*\d+(?:[,.]\d+)?\s*([^%]+?)(?=%\s*\d|$)", re.IGNORECASE
)
_TRAILING_PERCENT_REGEX = re.compile(
    r"([^%]+?)\s*%\s*\d+(?:[,.]\d+)?(?=$|[,+/&-])", re.IGNORECASE
)


def _is_numeric_expression(val):
    if _NUMERIC_FRACTION_REGEX.search(val):
        return True
    if _LEADS_WITH_NUMBER_REGEX.match(val):
        return True
    return False


def _strip_ratio_noise(part):
    part = re.sub(r"\b\d+(?:[,.]\d+)?\s*%", " ", part)
    part = re.sub(r"%\s*\d+(?:[,.]\d+)?", " ", part)
    part = re.sub(r"\s+", " ", part)
    return part.strip()


def _split_percent_value(val):
    if "%" not in val:
        return []
    parts = []
    for match in _PERCENT_PART_REGEX.finditer(val):
        cleaned = _strip_ratio_noise(match.group(1))
        if cleaned:
            parts.append(cleaned)
    if parts:
        return parts
    for match in _TRAILING_PERCENT_REGEX.finditer(val):
        cleaned = _strip_ratio_noise(match.group(1))
        if cleaned:
            parts.append(cleaned)
    return parts


def split_composite_value(val, group_name=None):
    if not val:
        return []
    if group_name == "Marka":
        return [val.strip()]

    val_stripped = val.strip()

    percent_parts = _split_percent_value(val_stripped)
    if percent_parts:
        result = []
        for part in percent_parts:
            result.extend(split_composite_value(part, group_name=group_name))
        return result

    if _is_numeric_expression(val_stripped):
        return [val_stripped]

    parts = COMPOSITE_SPLIT_REGEX.split(val)
    return [_strip_ratio_noise(p) for p in parts if p and _strip_ratio_noise(p)]


# ==========================================
# TEK DEĞER NORMALİZASYONU
# ==========================================
def normalize_single_value(val, group_name=None):
    if not val:
        return None
    cleaned = clean_filter_value(val)
    if not cleaned:
        return None
    lower = tr_lower(cleaned)

    if group_name == "Marka":
        return cleaned

    if is_junk(lower, group_name=group_name):
        return None

    group_aliases = _GROUP_ALIASES.get(group_name, {})
    if lower in group_aliases:
        return group_aliases[lower]

    # Beden: Özdilek ham yaş/ay formatları ("10yas"→"10 Yaş", "6/7yas"→"6-7 Yaş")
    if group_name == "Beden":
        m = _BEDEN_AGE_RANGE_RE.match(lower)
        if m:
            return f"{m.group(1)}-{m.group(2)} Yaş"
        m = _BEDEN_MONTH_RANGE_RE.match(lower)
        if m:
            return f"{m.group(1)}-{m.group(2)} Ay"
        m = _BEDEN_AGE_RE.match(lower)
        if m:
            return f"{m.group(1)} Yaş"

    result = tr_title(cleaned)

    # Beden boyut kısaltması düzeltme: "2xl" → "2XL", "Xl" → "XL"
    m = _SIZE_RE.match(result)
    if m:
        return m.group(1) + m.group(2).upper()

    # Boyut aralığı: "2xl-3xl" → "2XL-3XL"
    mr = _SIZE_RANGE_RE.match(result)
    if mr:
        def _up(s):
            mm = _SIZE_RE.match(s)
            return mm.group(1) + mm.group(2).upper() if mm else s.upper()
        return _up(mr.group(1)) + "-" + _up(mr.group(2))

    return result


# ==========================================
# LİSTE NORMALİZASYONU
# ==========================================
def normalize_value_list(value_list, group_name=None):
    seen = set()
    result = []

    for raw_val in value_list:
        cleaned = clean_filter_value(raw_val)
        if not cleaned:
            continue

        parts = split_composite_value(cleaned, group_name=group_name)

        for part in parts:
            normalized = normalize_single_value(part, group_name=group_name)
            if not normalized:
                continue
            key = tr_lower(normalized)
            if key in seen:
                continue
            seen.add(key)
            result.append(normalized)

    return sorted(result)
