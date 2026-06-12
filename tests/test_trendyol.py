from unittest.mock import patch, MagicMock
from sources.trendyol import fetch_aggregations, path_model_from_url


def test_path_model_from_url():
    assert path_model_from_url("https://www.trendyol.com/abiye-x-c56?pi=2") == "abiye-x-c56"


def test_fetch_aggregations_parses_groups():
    resp = MagicMock(status_code=200)
    resp.json.return_value = {"aggregation": [
        {"title": "Renk", "values": [{"text": "Kırmızı"}, {"text": "Siyah"}]},
        {"title": "Boş", "values": []},
    ]}
    with patch("sources.trendyol.requests.get", return_value=resp):
        out = fetch_aggregations("https://www.trendyol.com/abiye-x-c56")
    assert out == {"Renk": ["Kırmızı", "Siyah"]}


def test_fetch_aggregations_network_error_returns_empty():
    with patch("sources.trendyol.requests.get", side_effect=Exception("boom")):
        assert fetch_aggregations("https://www.trendyol.com/abiye-x-c56") == {}


def test_fetch_aggregations_shape_drift_returns_empty():
    resp = MagicMock(status_code=200)
    resp.json.return_value = {"aggregation": [{"title": "Renk", "values": ["düz-string"]}]}
    with patch("sources.trendyol.requests.get", return_value=resp):
        assert fetch_aggregations("https://www.trendyol.com/abiye-x-c56") == {}
