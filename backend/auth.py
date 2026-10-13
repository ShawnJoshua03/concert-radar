import os
import secrets
import time
import urllib.parse
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt

import queries
from database import get_db
from models import UserResponse

router = APIRouter()

_SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
_SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
_SPOTIFY_ME_URL    = "https://api.spotify.com/v1/me"
_SCOPES = "user-read-private user-read-email user-top-read user-read-recently-played"

# Server-side state store avoids cookie domain issues (e.g. localhost vs 127.0.0.1 in dev)
_oauth_states: dict[str, float] = {}  # state -> expiry unix timestamp
_STATE_TTL = 600  # 10 minutes
_TOKEN_REFRESH_MARGIN = timedelta(seconds=60)


def _store_state(state: str) -> None:
    now = time.time()
    expired = [k for k, v in _oauth_states.items() if v < now]
    for k in expired:
        del _oauth_states[k]
    _oauth_states[state] = now + _STATE_TTL


def _consume_state(state: str) -> bool:
    expiry = _oauth_states.pop(state, None)
    return expiry is not None and time.time() < expiry


def _is_prod() -> bool:
    return os.getenv("ENVIRONMENT", "development") == "production"


def _create_session_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=30),
    }
    return jwt.encode(payload, os.getenv("SECRET_KEY"), algorithm="HS256")


def _decode_session_token(token: str) -> str:
    payload = jwt.decode(token, os.getenv("SECRET_KEY"), algorithms=["HS256"])
    return payload["sub"]


def get_current_user_id(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        return _decode_session_token(auth[len("Bearer "):])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid session") from None


def _request_refreshed_tokens(refresh_token: str) -> dict:
    token_resp = httpx.post(
        _SPOTIFY_TOKEN_URL,
        data={"grant_type": "refresh_token", "refresh_token": refresh_token},
        auth=(os.getenv("SPOTIFY_CLIENT_ID"), os.getenv("SPOTIFY_CLIENT_SECRET")),
        timeout=10,
    )
    if token_resp.status_code in (400, 401):
        raise HTTPException(status_code=401, detail="Spotify session expired — please log in again")
    token_resp.raise_for_status()
    return token_resp.json()


def _refresh_and_store(user: dict) -> str:
    if not user["refresh_token"]:
        raise HTTPException(status_code=401, detail="Spotify session expired — please log in again")
    tokens = _request_refreshed_tokens(user["refresh_token"])
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(queries.UPDATE_TOKENS, {
                "access_token":     tokens["access_token"],
                # Spotify only sometimes rotates the refresh token
                "refresh_token":    tokens.get("refresh_token", user["refresh_token"]),
                "token_expires_at": datetime.now(timezone.utc) + timedelta(seconds=tokens["expires_in"]),
                "user_id":          str(user["id"]),
            })
    return tokens["access_token"]


def get_spotify_access_token(user: dict) -> str:
    """Returns a usable Spotify access token, refreshing it first if it's about to expire."""
    expires_at = user["token_expires_at"]
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at is None or expires_at - _TOKEN_REFRESH_MARGIN > datetime.now(timezone.utc):
        return user["access_token"]
    return _refresh_and_store(user)


@router.get("/login")
def login():
    state = secrets.token_urlsafe(16)
    _store_state(state)
    params = urllib.parse.urlencode({
        "client_id":    os.getenv("SPOTIFY_CLIENT_ID"),
        "response_type": "code",
        "redirect_uri": os.getenv("SPOTIFY_REDIRECT_URI"),
        "state":        state,
        "scope":        _SCOPES,
    })
    return RedirectResponse(f"{_SPOTIFY_AUTH_URL}?{params}")


@router.get("/callback")
def callback(request: Request, code: str = None, state: str = None, error: str = None):
    frontend_url = os.getenv("FRONTEND_URL")

    if error:
        return RedirectResponse(f"{frontend_url}?error={urllib.parse.quote(error)}")

    if not state or not _consume_state(state):
        raise HTTPException(status_code=400, detail="State mismatch — possible CSRF")

    token_resp = httpx.post(
        _SPOTIFY_TOKEN_URL,
        data={
            "grant_type":   "authorization_code",
            "code":         code,
            "redirect_uri": os.getenv("SPOTIFY_REDIRECT_URI"),
        },
        auth=(os.getenv("SPOTIFY_CLIENT_ID"), os.getenv("SPOTIFY_CLIENT_SECRET")),
        timeout=10,
    )
    token_resp.raise_for_status()
    tokens = token_resp.json()

    access_token     = tokens["access_token"]
    refresh_token    = tokens.get("refresh_token")
    token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=tokens["expires_in"])

    profile_resp = httpx.get(
        _SPOTIFY_ME_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    profile_resp.raise_for_status()
    profile = profile_resp.json()

    avatar_url = profile["images"][0]["url"] if profile.get("images") else None

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(queries.UPSERT_USER, {
                "spotify_id":       profile["id"],
                "display_name":     profile.get("display_name"),
                "email":            profile.get("email"),
                "avatar_url":       avatar_url,
                "access_token":     access_token,
                "refresh_token":    refresh_token,
                "token_expires_at": token_expires_at,
            })
            user = cur.fetchone()

    session_token = _create_session_token(str(user["id"]))
    return RedirectResponse(f"{frontend_url}?token={session_token}")


@router.get("/me", response_model=UserResponse)
def me(request: Request):
    user_id = get_current_user_id(request)

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(queries.GET_USER_BY_ID, {"user_id": user_id})
            user = cur.fetchone()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse(
        id=str(user["id"]),
        spotify_id=user["spotify_id"],
        display_name=user["display_name"],
        email=user["email"],
        avatar_url=user["avatar_url"],
        city=user["city"],
    )


@router.post("/logout")
def logout():
    return {"ok": True}


@router.post("/refresh")
def refresh(request: Request):
    user_id = get_current_user_id(request)

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(queries.GET_USER_BY_ID, {"user_id": user_id})
            user = cur.fetchone()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    _refresh_and_store(user)
    return {"ok": True}
