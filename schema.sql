-- Run this in your Supabase SQL editor

CREATE TABLE IF NOT EXISTS users (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    spotify_id       TEXT UNIQUE NOT NULL,
    display_name     TEXT,
    email            TEXT,
    avatar_url       TEXT,
    city             TEXT,
    access_token     TEXT NOT NULL,
    refresh_token    TEXT,
    token_expires_at TIMESTAMPTZ,
    created_at       TIMESTAMPTZ DEFAULT NOW(),
    updated_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_artists (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    artist_id        TEXT NOT NULL,
    artist_name      TEXT NOT NULL,
    artist_image_url TEXT,
    affinity_score   NUMERIC(5,2),
    genres           TEXT[],
    updated_at       TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, artist_id)
);

CREATE TABLE IF NOT EXISTS shows (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    artist_id  TEXT NOT NULL,
    event_id   TEXT UNIQUE NOT NULL,
    event_name TEXT,
    venue_name TEXT,
    venue_city TEXT,
    event_date TIMESTAMPTZ,
    ticket_url TEXT,
    price_min  NUMERIC(10,2),
    price_max  NUMERIC(10,2),
    cached_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Phase 4: run these if upgrading an existing database
ALTER TABLE users ADD COLUMN IF NOT EXISTS lat NUMERIC(9,6);
ALTER TABLE users ADD COLUMN IF NOT EXISTS lng NUMERIC(9,6);

CREATE INDEX IF NOT EXISTS idx_user_artists_user_id  ON user_artists(user_id);
CREATE INDEX IF NOT EXISTS idx_user_artists_affinity ON user_artists(affinity_score DESC);
CREATE INDEX IF NOT EXISTS idx_shows_artist_id       ON shows(artist_id);
CREATE INDEX IF NOT EXISTS idx_shows_event_date      ON shows(event_date);
CREATE INDEX IF NOT EXISTS idx_shows_cached_at       ON shows(cached_at);
