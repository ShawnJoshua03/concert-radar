import os
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher

import httpx

_BASE_URL = "https://app.ticketmaster.com/discovery/v2/events.json"
_DEFAULT_LAT = 39.1031   # Cincinnati fallback
_DEFAULT_LNG = -84.5120
_RADIUS = 50
_ATTRACTION_THRESHOLD = 0.70
_FALLBACK_THRESHOLD   = 0.82


def _ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def _matches_artist(event: dict, artist_name: str) -> bool:
    attractions = event.get("_embedded", {}).get("attractions", [])
    if attractions:
        return any(_ratio(a.get("name", ""), artist_name) >= _ATTRACTION_THRESHOLD
                   for a in attractions)
    return _ratio(event.get("name", ""), artist_name) >= _FALLBACK_THRESHOLD


def fetch_events_for_artist(
    artist_name: str,
    lat: float = _DEFAULT_LAT,
    lng: float = _DEFAULT_LNG,
) -> list[dict]:
    api_key = os.getenv("TICKETMASTER_API_KEY", "")
    if not api_key or api_key == "your_ticketmaster_api_key":
        return []

    now = datetime.now(timezone.utc)
    end = now + timedelta(days=180)

    params = {
        "apikey":             api_key,
        "keyword":            artist_name,
        "latlong":            f"{lat},{lng}",
        "radius":             _RADIUS,
        "unit":               "miles",
        "classificationName": "music",
        "startDateTime":      now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "endDateTime":        end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "size":               20,
        "sort":               "date,asc",
    }

    try:
        resp = httpx.get(_BASE_URL, params=params, timeout=10)
        resp.raise_for_status()
    except httpx.HTTPError:
        return []

    events = resp.json().get("_embedded", {}).get("events", [])
    results = []
    for event in events:
        if not _matches_artist(event, artist_name):
            continue

        start = event.get("dates", {}).get("start", {})
        date_str = start.get("dateTime") or start.get("localDate")
        if not date_str:
            continue
        if "T" not in date_str:
            date_str = f"{date_str}T12:00:00Z"

        venues = event.get("_embedded", {}).get("venues", [])
        venue = venues[0] if venues else {}
        city  = venue.get("city", {}).get("name", "")
        state = venue.get("state", {}).get("stateCode", "")
        venue_city = f"{city}, {state}" if state else city

        price_ranges = event.get("priceRanges", [])
        price = price_ranges[0] if price_ranges else {}

        results.append({
            "event_id":   event["id"],
            "event_name": event.get("name", ""),
            "venue_name": venue.get("name", ""),
            "venue_city": venue_city,
            "event_date": date_str,
            "ticket_url": event.get("url", ""),
            "price_min":  price.get("min"),
            "price_max":  price.get("max"),
        })

    return results
