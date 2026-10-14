from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Request

import queries
from auth import get_current_user_id
from database import get_db
from models import ConcertResponse, ConcertsListResponse
from ticketmaster_client import DEFAULT_LAT, DEFAULT_LNG, fetch_events_for_artist

router = APIRouter()

_CACHE_TTL = timedelta(hours=6)
_MAX_ARTISTS_TO_SEARCH = 20


def _is_fresh(fetched_at: datetime | None) -> bool:
    if fetched_at is None:
        return False
    if fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - fetched_at < _CACHE_TTL


@router.get("", response_model=ConcertsListResponse)
def get_concerts(request: Request):
    user_id = get_current_user_id(request)

    # ── Step 1: user coords + cache check + artist list ───────────────────────
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(queries.GET_USER_BY_ID, {"user_id": user_id})
            user = cur.fetchone()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            lat = float(user["lat"]) if user["lat"] is not None else DEFAULT_LAT
            lng = float(user["lng"]) if user["lng"] is not None else DEFAULT_LNG

            # Tracked per user (not via MIN(cached_at)) so a city with zero
            # matching shows still counts as cached instead of re-querying
            # Ticketmaster on every page load.
            needs_refresh = not _is_fresh(user["concerts_fetched_at"])

            artists_to_search = []
            if needs_refresh:
                cur.execute(queries.GET_TOP_ARTISTS, {
                    "user_id": user_id,
                    "limit": _MAX_ARTISTS_TO_SEARCH,
                })
                artists_to_search = cur.fetchall()

    # ── Step 2: Ticketmaster — outside DB transaction ─────────────────────────
    new_shows: list[dict] = []
    if needs_refresh:
        for artist in artists_to_search:
            for ev in fetch_events_for_artist(artist["artist_name"], lat, lng):
                new_shows.append({"user_id": user_id, "artist_id": artist["artist_id"], **ev})

    # ── Step 3: persist + return ──────────────────────────────────────────────
    with get_db() as conn:
        with conn.cursor() as cur:
            if needs_refresh:
                cur.execute(queries.DELETE_USER_SHOWS, {"user_id": user_id})
                for show in new_shows:
                    cur.execute(queries.UPSERT_SHOW, show)
                cur.execute(queries.DELETE_STALE_SHOWS)
                cur.execute(queries.MARK_CONCERTS_FETCHED, {"user_id": user_id})

            cur.execute(queries.GET_CONCERTS_FOR_USER, {"user_id": user_id})
            rows = cur.fetchall()

    concerts = [
        ConcertResponse(
            event_id=r["event_id"],
            event_name=r["event_name"],
            venue_name=r["venue_name"],
            venue_city=r["venue_city"],
            event_date=r["event_date"].isoformat() if r["event_date"] else None,
            ticket_url=r["ticket_url"],
            price_min=float(r["price_min"]) if r["price_min"] is not None else None,
            price_max=float(r["price_max"]) if r["price_max"] is not None else None,
            artist_id=r["artist_id"],
            artist_name=r["artist_name"],
            artist_image_url=r["artist_image_url"],
            affinity_score=float(r["affinity_score"]),
            genres=list(r["genres"] or []),
        )
        for r in rows
    ]
    return ConcertsListResponse(total=len(concerts), concerts=concerts)
