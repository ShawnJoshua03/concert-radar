-- Run this in your Supabase SQL editor (safe to re-run)

CREATE TABLE IF NOT EXISTS users (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    spotify_id          TEXT UNIQUE NOT NULL,
    display_name        TEXT,
    email               TEXT,
    avatar_url          TEXT,
    city                TEXT,
    lat                 NUMERIC(9,6),
    lng                 NUMERIC(9,6),
    access_token        TEXT NOT NULL,
    refresh_token       TEXT,
    token_expires_at    TIMESTAMPTZ,
    concerts_fetched_at TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
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

-- Shows are a per-user cache: the same event can be cached for several users,
-- and each user's cache reflects the Ticketmaster search around *their* city.
CREATE TABLE IF NOT EXISTS shows (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    artist_id  TEXT NOT NULL,
    event_id   TEXT NOT NULL,
    event_name TEXT,
    venue_name TEXT,
    venue_city TEXT,
    event_date TIMESTAMPTZ,
    ticket_url TEXT,
    price_min  NUMERIC(10,2),
    price_max  NUMERIC(10,2),
    cached_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, event_id)
);

-- ── Migrations for databases created from earlier versions ───────────────────
ALTER TABLE users ADD COLUMN IF NOT EXISTS lat NUMERIC(9,6);
ALTER TABLE users ADD COLUMN IF NOT EXISTS lng NUMERIC(9,6);
ALTER TABLE users ADD COLUMN IF NOT EXISTS concerts_fetched_at TIMESTAMPTZ;

-- v1 cached shows globally by event_id; the cache is disposable, so clear it
-- and re-key it per user.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'shows' AND column_name = 'user_id'
    ) THEN
        TRUNCATE shows;
        ALTER TABLE shows DROP CONSTRAINT IF EXISTS shows_event_id_key;
        ALTER TABLE shows ADD COLUMN user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE;
        ALTER TABLE shows ADD CONSTRAINT shows_user_id_event_id_key UNIQUE (user_id, event_id);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_user_artists_user_id  ON user_artists(user_id);
CREATE INDEX IF NOT EXISTS idx_user_artists_affinity ON user_artists(affinity_score DESC);
CREATE INDEX IF NOT EXISTS idx_shows_user_id         ON shows(user_id);
CREATE INDEX IF NOT EXISTS idx_shows_event_date      ON shows(event_date);
