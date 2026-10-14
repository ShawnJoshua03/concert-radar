# ── Users ────────────────────────────────────────────────────────────────────

UPSERT_USER = """
    INSERT INTO users (spotify_id, display_name, email, avatar_url, access_token, refresh_token, token_expires_at)
    VALUES (%(spotify_id)s, %(display_name)s, %(email)s, %(avatar_url)s, %(access_token)s, %(refresh_token)s, %(token_expires_at)s)
    ON CONFLICT (spotify_id) DO UPDATE SET
        display_name     = EXCLUDED.display_name,
        email            = EXCLUDED.email,
        avatar_url       = EXCLUDED.avatar_url,
        access_token     = EXCLUDED.access_token,
        refresh_token    = EXCLUDED.refresh_token,
        token_expires_at = EXCLUDED.token_expires_at,
        updated_at       = NOW()
    RETURNING id, spotify_id, display_name, email, avatar_url, city
"""

GET_USER_BY_ID = """
    SELECT id, spotify_id, display_name, email, avatar_url, city,
           lat, lng, access_token, refresh_token, token_expires_at,
           concerts_fetched_at
    FROM users
    WHERE id = %(user_id)s
"""

UPDATE_TOKENS = """
    UPDATE users SET
        access_token     = %(access_token)s,
        refresh_token    = %(refresh_token)s,
        token_expires_at = %(token_expires_at)s,
        updated_at       = NOW()
    WHERE id = %(user_id)s
"""

UPDATE_CITY = """
    UPDATE users SET city = %(city)s, lat = %(lat)s, lng = %(lng)s, updated_at = NOW()
    WHERE id = %(user_id)s
"""

MARK_CONCERTS_FETCHED = """
    UPDATE users SET concerts_fetched_at = NOW() WHERE id = %(user_id)s
"""

INVALIDATE_CONCERTS = """
    UPDATE users SET concerts_fetched_at = NULL WHERE id = %(user_id)s
"""

DELETE_USER_SHOWS = """
    DELETE FROM shows WHERE user_id = %(user_id)s
"""

# ── Artists ───────────────────────────────────────────────────────────────────

UPSERT_ARTIST = """
    INSERT INTO user_artists (user_id, artist_id, artist_name, artist_image_url, affinity_score, genres, updated_at)
    VALUES (%(user_id)s, %(artist_id)s, %(artist_name)s, %(artist_image_url)s, %(affinity_score)s, %(genres)s, NOW())
    ON CONFLICT (user_id, artist_id) DO UPDATE SET
        artist_name      = EXCLUDED.artist_name,
        artist_image_url = EXCLUDED.artist_image_url,
        affinity_score   = EXCLUDED.affinity_score,
        genres           = EXCLUDED.genres,
        updated_at       = NOW()
"""

DELETE_ARTISTS_NOT_IN = """
    DELETE FROM user_artists
    WHERE user_id = %(user_id)s AND NOT (artist_id = ANY(%(artist_ids)s))
"""

GET_TOP_ARTISTS = """
    SELECT artist_id, artist_name, artist_image_url, affinity_score, genres
    FROM user_artists
    WHERE user_id = %(user_id)s
    ORDER BY affinity_score DESC
    LIMIT %(limit)s
"""

# ── Shows ─────────────────────────────────────────────────────────────────────

UPSERT_SHOW = """
    INSERT INTO shows (user_id, artist_id, event_id, event_name, venue_name, venue_city, event_date, ticket_url, price_min, price_max, cached_at)
    VALUES (%(user_id)s, %(artist_id)s, %(event_id)s, %(event_name)s, %(venue_name)s, %(venue_city)s, %(event_date)s, %(ticket_url)s, %(price_min)s, %(price_max)s, NOW())
    ON CONFLICT (user_id, event_id) DO UPDATE SET
        artist_id  = EXCLUDED.artist_id,
        event_name = EXCLUDED.event_name,
        venue_name = EXCLUDED.venue_name,
        venue_city = EXCLUDED.venue_city,
        event_date = EXCLUDED.event_date,
        ticket_url = EXCLUDED.ticket_url,
        price_min  = EXCLUDED.price_min,
        price_max  = EXCLUDED.price_max,
        cached_at  = NOW()
"""

GET_CONCERTS_FOR_USER = """
    SELECT
        s.event_id,
        s.event_name,
        s.venue_name,
        s.venue_city,
        s.event_date,
        s.ticket_url,
        s.price_min,
        s.price_max,
        ua.artist_id,
        ua.artist_name,
        ua.artist_image_url,
        ua.affinity_score,
        ua.genres
    FROM shows s
    JOIN user_artists ua ON ua.artist_id = s.artist_id AND ua.user_id = s.user_id
    WHERE s.user_id = %(user_id)s
      AND s.event_date >= NOW()
      AND s.event_date <= NOW() + INTERVAL '6 months'
    ORDER BY ua.affinity_score DESC, s.event_date ASC
"""

DELETE_STALE_SHOWS = """
    DELETE FROM shows WHERE event_date < NOW() - INTERVAL '1 day'
"""
