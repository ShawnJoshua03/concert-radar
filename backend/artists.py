import httpx
from fastapi import APIRouter, HTTPException, Request

import queries
from auth import get_current_user_id, get_spotify_access_token
from database import get_db
from models import ArtistResponse, SyncResponse

router = APIRouter()

_SPOTIFY_TOP_ARTISTS_URL = "https://api.spotify.com/v1/me/top/artists"
_TIME_RANGES = ("short_term", "medium_term", "long_term")
_WEIGHTS = {"short_term": 3, "medium_term": 2, "long_term": 1}
_LIMIT = 50
_MAX_RAW = _LIMIT * sum(_WEIGHTS.values())  # 50 × 6 = 300


def _fetch_range(access_token: str, time_range: str) -> list[dict]:
    resp = httpx.get(
        _SPOTIFY_TOP_ARTISTS_URL,
        params={"time_range": time_range, "limit": _LIMIT},
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    if resp.status_code == 401:
        raise HTTPException(status_code=401, detail="Spotify token expired. Please log in again.")
    resp.raise_for_status()
    return resp.json().get("items", [])


def _compute_scores(range_artists: dict[str, list]) -> dict[str, dict]:
    scores: dict[str, dict] = {}
    for time_range, artists in range_artists.items():
        weight = _WEIGHTS[time_range]
        for idx, artist in enumerate(artists):
            aid = artist["id"]
            rank_score = _LIMIT - idx  # #1 → 50, #50 → 1
            if aid not in scores:
                image_url = artist["images"][0]["url"] if artist.get("images") else None
                scores[aid] = {
                    "name": artist["name"],
                    "image_url": image_url,
                    "genres": artist.get("genres", []),
                    "raw": 0,
                }
            scores[aid]["raw"] += rank_score * weight
    for data in scores.values():
        data["affinity"] = round(data["raw"] / _MAX_RAW * 100, 2)
    return scores


def _rows_to_artists(rows) -> list[ArtistResponse]:
    return [
        ArtistResponse(
            artist_id=row["artist_id"],
            artist_name=row["artist_name"],
            artist_image_url=row["artist_image_url"],
            affinity_score=float(row["affinity_score"]),
            genres=list(row["genres"] or []),
        )
        for row in rows
    ]


@router.get("", response_model=SyncResponse)
def get_artists(request: Request):
    user_id = get_current_user_id(request)
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(queries.GET_TOP_ARTISTS, {"user_id": user_id, "limit": _LIMIT})
            rows = cur.fetchall()
    artists = _rows_to_artists(rows)
    return SyncResponse(synced=len(artists), artists=artists)


@router.post("/sync", response_model=SyncResponse)
def sync(request: Request):
    user_id = get_current_user_id(request)

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(queries.GET_USER_BY_ID, {"user_id": user_id})
            user = cur.fetchone()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    access_token = get_spotify_access_token(user)
    range_artists = {tr: _fetch_range(access_token, tr) for tr in _TIME_RANGES}
    scores = _compute_scores(range_artists)

    with get_db() as conn:
        with conn.cursor() as cur:
            for aid, data in scores.items():
                cur.execute(queries.UPSERT_ARTIST, {
                    "user_id":          user_id,
                    "artist_id":        aid,
                    "artist_name":      data["name"],
                    "artist_image_url": data["image_url"],
                    "affinity_score":   data["affinity"],
                    "genres":           data["genres"],
                })
            # Drop artists that fell out of every top-50 list, and force the
            # concert feed to re-search with the new artist set.
            cur.execute(queries.DELETE_ARTISTS_NOT_IN, {
                "user_id":    user_id,
                "artist_ids": list(scores.keys()),
            })
            cur.execute(queries.INVALIDATE_CONCERTS, {"user_id": user_id})

    artists = sorted(
        [
            ArtistResponse(
                artist_id=aid,
                artist_name=data["name"],
                artist_image_url=data["image_url"],
                affinity_score=data["affinity"],
                genres=data["genres"],
            )
            for aid, data in scores.items()
        ],
        key=lambda a: a.affinity_score,
        reverse=True,
    )
    return SyncResponse(synced=len(artists), artists=artists)
