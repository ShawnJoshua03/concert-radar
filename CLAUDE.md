# Concert Radar

Find concerts ranked by how much you actually listen to the artist.

## Stack
- Backend: FastAPI + Python, PostgreSQL (Supabase)
- Frontend: Vanilla JS + D3.js
- Deploy: Vercel (frontend) + Render (backend)
- APIs: Spotify Web API, Ticketmaster Discovery API, OpenStreetMap Nominatim (geocoding)

## Conventions
- D3 charts are reusable functions: createX(selector, data, options)
- All secrets via .env, never hardcoded
- SQL queries live in queries.py only
- All HTTP calls from frontend go through api.js (never fetch directly)
- Pydantic response models live in models.py

## Current Phase
Phase 1 complete — Spotify OAuth (login → callback → session cookie → /auth/me → dashboard)
Next: Phase 2 — pull top artists (3 time ranges), compute affinity scores, store in user_artists
