from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi import HTTPException

import auth
import concerts
import main
import queries


class TestAuth:
    def test_health(self, client):
        assert client.get("/").json() == {"status": "ok", "app": "Concert Radar"}

    @pytest.mark.parametrize("path", ["/auth/me", "/artists", "/concerts"])
    def test_protected_routes_require_token(self, client, path):
        assert client.get(path).status_code == 401

    def test_invalid_token_rejected(self, client):
        resp = client.get("/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
        assert resp.status_code == 401

    def test_token_signed_with_other_key_rejected(self, client):
        from jose import jwt

        forged = jwt.encode({"sub": "someone"}, "wrong-key", algorithm="HS256")
        resp = client.get("/auth/me", headers={"Authorization": f"Bearer {forged}"})
        assert resp.status_code == 401

    def test_login_redirects_to_spotify_with_state(self, client):
        resp = client.get("/auth/login", follow_redirects=False)
        assert resp.status_code == 307
        location = urlsplit(resp.headers["location"])
        params = parse_qs(location.query)
        assert location.netloc == "accounts.spotify.com"
        assert params["client_id"] == ["test-client-id"]
        assert params["state"][0] in auth._oauth_states

    def test_callback_rejects_unknown_state(self, client):
        resp = client.get("/auth/callback", params={"code": "c", "state": "forged"}, follow_redirects=False)
        assert resp.status_code == 400

    def test_state_is_single_use(self):
        auth._store_state("abc")
        assert auth._consume_state("abc") is True
        assert auth._consume_state("abc") is False

    def test_me_returns_profile(self, client, fake_db, user_row, auth_header):
        fake_db.responses[queries.GET_USER_BY_ID] = user_row
        body = client.get("/auth/me", headers=auth_header).json()
        assert body["display_name"] == "Test User"
        assert body["city"] == "Chicago, IL"
        assert "access_token" not in body


class TestSpotifyTokenRefresh:
    def test_valid_token_is_reused(self, fake_db, user_row, monkeypatch):
        monkeypatch.setattr(auth, "_request_refreshed_tokens", lambda _: pytest.fail("should not refresh"))
        assert auth.get_spotify_access_token(user_row) == "access-old"
        assert fake_db.executed == []

    def test_expired_token_is_refreshed_and_stored(self, fake_db, user_row, monkeypatch):
        user_row["token_expires_at"] = datetime.now(timezone.utc) - timedelta(minutes=5)
        monkeypatch.setattr(auth, "_request_refreshed_tokens",
                            lambda token: {"access_token": "access-new", "expires_in": 3600})

        assert auth.get_spotify_access_token(user_row) == "access-new"
        [params] = fake_db.params_for(queries.UPDATE_TOKENS)
        assert params["access_token"] == "access-new"
        assert params["refresh_token"] == "refresh-old"  # kept when Spotify doesn't rotate it

    def test_naive_expiry_treated_as_utc(self, fake_db, user_row, monkeypatch):
        user_row["token_expires_at"] = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=2)
        monkeypatch.setattr(auth, "_request_refreshed_tokens",
                            lambda token: {"access_token": "access-new", "expires_in": 3600})
        assert auth.get_spotify_access_token(user_row) == "access-new"

    def test_missing_refresh_token_asks_user_to_log_in(self, fake_db, user_row):
        user_row["token_expires_at"] = datetime.now(timezone.utc) - timedelta(minutes=5)
        user_row["refresh_token"] = None
        with pytest.raises(HTTPException) as exc:
            auth.get_spotify_access_token(user_row)
        assert exc.value.status_code == 401


class TestConcertCache:
    def test_is_fresh(self):
        now = datetime.now(timezone.utc)
        assert not concerts._is_fresh(None)
        assert concerts._is_fresh(now - timedelta(hours=1))
        assert not concerts._is_fresh(now - timedelta(hours=7))
        assert concerts._is_fresh((now - timedelta(hours=1)).replace(tzinfo=None))

    def test_fresh_cache_skips_ticketmaster(self, client, fake_db, user_row, auth_header, monkeypatch):
        user_row["concerts_fetched_at"] = datetime.now(timezone.utc) - timedelta(minutes=10)
        fake_db.responses[queries.GET_USER_BY_ID] = user_row
        monkeypatch.setattr(concerts, "fetch_events_for_artist", lambda *a: pytest.fail("cache was fresh"))

        resp = client.get("/concerts", headers=auth_header)
        assert resp.status_code == 200
        assert resp.json() == {"total": 0, "concerts": []}

    def test_stale_cache_refetches_for_this_user_only(self, client, fake_db, user_row, auth_header,
                                                      monkeypatch):
        fake_db.responses[queries.GET_USER_BY_ID] = user_row
        fake_db.responses[queries.GET_TOP_ARTISTS] = [{"artist_id": "a1", "artist_name": "Phoebe Bridgers"}]
        calls = []

        def fake_fetch(name, lat, lng):
            calls.append((name, lat, lng))
            return [{"event_id": "ev1", "event_name": "Show", "venue_name": "V", "venue_city": "Chicago, IL",
                     "event_date": "2026-11-20T01:00:00Z", "ticket_url": "", "price_min": None,
                     "price_max": None}]

        monkeypatch.setattr(concerts, "fetch_events_for_artist", fake_fetch)
        assert client.get("/concerts", headers=auth_header).status_code == 200

        assert calls == [("Phoebe Bridgers", 41.8781, -87.6298)]  # searched around the user's city
        [show] = fake_db.params_for(queries.UPSERT_SHOW)
        assert show["user_id"] == user_row["id"]
        assert fake_db.params_for(queries.DELETE_USER_SHOWS) == [{"user_id": user_row["id"]}]
        assert fake_db.params_for(queries.MARK_CONCERTS_FETCHED) == [{"user_id": user_row["id"]}]

    def test_changing_city_invalidates_only_this_users_cache(self, client, fake_db, user_row, auth_header,
                                                             monkeypatch):
        import users

        monkeypatch.setattr(users, "geocode_city", lambda city: (40.7128, -74.0060))
        resp = client.post("/user/city", json={"city": "New York, NY"}, headers=auth_header)
        assert resp.status_code == 200
        assert fake_db.params_for(queries.DELETE_USER_SHOWS) == [{"user_id": user_row["id"]}]
        assert fake_db.params_for(queries.INVALIDATE_CONCERTS) == [{"user_id": user_row["id"]}]

    def test_ungeocodable_city_returns_400(self, client, fake_db, auth_header, monkeypatch):
        import users

        monkeypatch.setattr(users, "geocode_city", lambda city: None)
        resp = client.post("/user/city", json={"city": "zzzz"}, headers=auth_header)
        assert resp.status_code == 400
        assert fake_db.executed == []


def test_cors_origin_strips_path():
    assert main._origin("https://shawnjoshua03.github.io/concert-radar/dashboard.html") == \
        "https://shawnjoshua03.github.io"
    assert main._origin("http://127.0.0.1:3000/dashboard.html") == "http://127.0.0.1:3000"


def test_sync_scores_prunes_stale_artists_and_invalidates_concerts(client, fake_db, user_row, auth_header,
                                                                   monkeypatch):
    import artists

    fake_db.responses[queries.GET_USER_BY_ID] = user_row
    monkeypatch.setattr(artists, "get_spotify_access_token", lambda user: "fresh-token")
    tokens_used = []

    def fake_fetch(token, time_range):
        tokens_used.append(token)
        return [{"id": "a1", "name": "Phoebe Bridgers"}] if time_range == "short_term" else []

    monkeypatch.setattr(artists, "_fetch_range", fake_fetch)
    body = client.post("/artists/sync", headers=auth_header).json()

    assert tokens_used == ["fresh-token"] * 3
    assert body["artists"][0]["affinity_score"] == 50.0
    [pruned] = fake_db.params_for(queries.DELETE_ARTISTS_NOT_IN)
    assert pruned == {"user_id": user_row["id"], "artist_ids": ["a1"]}
    assert fake_db.params_for(queries.INVALIDATE_CONCERTS) == [{"user_id": user_row["id"]}]
