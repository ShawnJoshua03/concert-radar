import httpx

import geocoding


def _respond(status=200, body=None, text=None):
    def fake_get(url, params, headers, timeout):
        request = httpx.Request("GET", url)
        if text is not None:
            return httpx.Response(status, text=text, request=request)
        return httpx.Response(status, json=body, request=request)
    return fake_get


def test_returns_coordinates_of_first_match(monkeypatch):
    monkeypatch.setattr(httpx, "get", _respond(body=[{"lat": "41.8755", "lon": "-87.6244"}]))
    assert geocoding.geocode_city("Chicago, IL") == (41.8755, -87.6244)


def test_no_match_or_bad_response_returns_none(monkeypatch):
    for fake in (_respond(body=[]), _respond(status=503), _respond(text="<html>busy</html>")):
        monkeypatch.setattr(httpx, "get", fake)
        assert geocoding.geocode_city("Nowhere") is None


def test_network_error_returns_none(monkeypatch):
    def boom(*args, **kwargs):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr(httpx, "get", boom)
    assert geocoding.geocode_city("Chicago, IL") is None
