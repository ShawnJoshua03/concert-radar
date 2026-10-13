import os
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

import pytest

# Set dummy config before any app module is imported, so load_dotenv() never
# fills these in from a developer's real backend/.env.
os.environ.update({
    "SECRET_KEY":            "test-secret",
    "DATABASE_URL":          "postgresql://test:test@127.0.0.1:1/test",
    "FRONTEND_URL":          "http://127.0.0.1:3000/dashboard.html",
    "SPOTIFY_CLIENT_ID":     "test-client-id",
    "SPOTIFY_CLIENT_SECRET": "test-client-secret",
    "SPOTIFY_REDIRECT_URI":  "http://127.0.0.1:8000/auth/callback",
    "TICKETMASTER_API_KEY":  "test-tm-key",
})


class FakeCursor:
    def __init__(self, db):
        self.db = db
        self._last = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        self.db.executed.append((sql, params))
        self._last = sql

    def fetchone(self):
        return self.db.responses.get(self._last)

    def fetchall(self):
        return self.db.responses.get(self._last, [])


class FakeConn:
    def __init__(self, db):
        self.db = db

    def cursor(self):
        return FakeCursor(self.db)


class FakeDB:
    """Stands in for get_db(): records every query and returns canned rows keyed by SQL string."""

    def __init__(self):
        self.responses = {}
        self.executed = []

    @contextmanager
    def connect(self):
        yield FakeConn(self)

    def params_for(self, sql):
        return [params for executed_sql, params in self.executed if executed_sql == sql]


@pytest.fixture
def fake_db(monkeypatch):
    import artists
    import auth
    import concerts
    import users

    db = FakeDB()
    for module in (artists, auth, concerts, users):
        monkeypatch.setattr(module, "get_db", db.connect)
    return db


@pytest.fixture
def user_row():
    return {
        "id":                  "11111111-1111-1111-1111-111111111111",
        "spotify_id":          "spotify-user",
        "display_name":        "Test User",
        "email":               "test@example.com",
        "avatar_url":          None,
        "city":                "Chicago, IL",
        "lat":                 41.8781,
        "lng":                 -87.6298,
        "access_token":        "access-old",
        "refresh_token":       "refresh-old",
        "token_expires_at":    datetime.now(timezone.utc) + timedelta(hours=1),
        "concerts_fetched_at": None,
    }


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    import main

    return TestClient(main.app)


@pytest.fixture
def auth_header(user_row):
    import auth

    return {"Authorization": f"Bearer {auth._create_session_token(user_row['id'])}"}
