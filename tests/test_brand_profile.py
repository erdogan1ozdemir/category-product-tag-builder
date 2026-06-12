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
