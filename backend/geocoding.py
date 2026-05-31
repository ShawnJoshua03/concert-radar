import httpx

_URL = "https://nominatim.openstreetmap.org/search"
_USER_AGENT = "ConcertRadar/1.0 (shawnlasrado@gmail.com)"


def geocode_city(city: str) -> tuple[float, float] | None:
    """Returns (lat, lng) for the best Nominatim match, or None."""
    try:
        resp = httpx.get(
            _URL,
            params={"q": city, "format": "json", "limit": 1},
            headers={"User-Agent": _USER_AGENT},
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json()
        if results:
            return float(results[0]["lat"]), float(results[0]["lon"])
    except Exception:
        pass
    return None
