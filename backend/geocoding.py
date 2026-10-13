import os

import httpx

_URL = "https://nominatim.openstreetmap.org/search"
# Nominatim's usage policy asks for an identifying User-Agent; set NOMINATIM_CONTACT
# to an email or URL so they can reach you if your traffic causes problems.
_USER_AGENT = f"ConcertRadar/1.0 ({os.getenv('NOMINATIM_CONTACT', 'https://github.com/ShawnJoshua03/concert-radar')})"


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
