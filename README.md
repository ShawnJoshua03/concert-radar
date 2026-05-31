# Concert Radar

**Find upcoming concerts ranked by how much you actually listen to the artist.**

Most concert apps sort by date or distance. Concert Radar sorts by *you* — it connects to your Spotify listening history, scores every artist with a weighted affinity algorithm across three time windows, then searches Ticketmaster for shows near your city. The artists you play on repeat always appear first.

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=flat-square&logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Supabase-3ECF8E?style=flat-square&logo=supabase&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-ES2022-F7DF1E?style=flat-square&logo=javascript&logoColor=black)
![D3.js](https://img.shields.io/badge/D3.js-v7-F9A03C?style=flat-square&logo=d3.js&logoColor=white)

---

## How It Works

```
  Spotify OAuth            Affinity Scoring         Ticketmaster Search
  ─────────────            ────────────────         ───────────────────
  Top artists ──► short_term  (w=3) ──►  raw score  ──►  keyword search
  (3 windows)     medium_term (w=2)       ÷ 300          per artist
                  long_term   (w=1)       × 100     ──►  fuzzy match
                                          = 0–100        to Spotify ID
                                              │
                                              ▼
                                      Ranked concert feed
                                      (affinity ↓, date ↑)
```

1. **Connect Spotify** — OAuth 2.0 login pulls your top 50 artists across three listening windows (last 4 weeks, last 6 months, all time) and stores them with rank position data.

2. **Affinity scoring** — each artist earns a 0–100 score that rewards recent heavy listening while still crediting long-term favourites. Scores persist in PostgreSQL and update on every sync.

3. **Concert search** — Ticketmaster is queried for each of your top 20 artists within 50 miles of your city. A `difflib` fuzzy matcher confirms each result actually belongs to the right artist before it's cached.

4. **Ranked feed** — results are sorted by affinity descending so the shows you'll care most about are always at the top. Ticketmaster data is cached for 6 hours; updating your city wipes the cache and re-fetches immediately.

---

## Affinity Score

Spotify exposes listening history across three time windows. Concert Radar fetches all three and weights them to reward **recent** heavy listening over stale long-term history:

| Time window | Covers | Weight |
|-------------|--------|--------|
| `short_term` | Last ~4 weeks | **3×** |
| `medium_term` | Last ~6 months | **2×** |
| `long_term` | All time | **1×** |

For each window the artist appears in, their list position is converted to a rank score and multiplied by the window weight:

```
rank_score   = 50 − list_index        # index 0 (most listened) → 50 pts
                                       # index 49 (least)        →  1 pt
contribution = rank_score × weight

raw_score = Σ contributions across every window the artist appears in
affinity  = round(raw_score / 300 × 100, 2)
```

The denominator **300** is the theoretical maximum — an artist ranked #1 in all three windows scores `(50×3) + (50×2) + (50×1) = 300`, which normalises to **100.00**. An artist you've only just started playing will score lower than one you've listened to for years *and* are currently obsessed with.

The D3 sidebar chart scales bars relative to your personal top artist, so the comparison is always meaningful regardless of absolute score values.

---

## Tech Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Backend API | Python 3.12, FastAPI | Async-ready; Pydantic v2 models |
| Database | PostgreSQL via Supabase | Connection pooling via psycopg2 |
| Authentication | Spotify OAuth 2.0 + HS256 JWT | Token stored in `localStorage`; sent as `Authorization: Bearer` |
| Frontend | Vanilla JS (ES2022) | No build step; ships directly to Vercel |
| Visualisation | D3.js v7 | `createAffinityChart(selector, data, options)` reusable bar chart |
| Geocoding | OpenStreetMap Nominatim | Free, no key required |
| Concert data | Ticketmaster Discovery API | Fuzzy-matched with `difflib.SequenceMatcher` |
| Hosting | Vercel (frontend) + Render (backend) | |

---

## Project Structure

```
concert-radar/
├── backend/
│   ├── main.py                  # FastAPI app + CORS middleware
│   ├── auth.py                  # Spotify OAuth flow, JWT helpers, /auth/* routes
│   ├── artists.py               # /artists/sync + /artists (affinity computation)
│   ├── concerts.py              # /concerts (6-hour cache + Ticketmaster dispatch)
│   ├── users.py                 # /user/city (geocode + save + cache invalidation)
│   ├── ticketmaster_client.py   # Ticketmaster API wrapper + fuzzy artist matching
│   ├── geocoding.py             # Nominatim geocoder
│   ├── queries.py               # All SQL — never inline
│   ├── models.py                # Pydantic response models
│   ├── database.py              # psycopg2 context manager
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── index.html               # Landing / login page
│   ├── dashboard.html           # Main application
│   ├── style.css
│   └── js/
│       ├── api.js               # apiFetch — all HTTP calls centralised here
│       ├── auth.js              # requireAuth, requireGuest, logout
│       └── charts.js            # createAffinityChart D3 reusable function
├── schema.sql                   # PostgreSQL schema + Phase 4 migration
├── vercel.json                  # Static frontend deployment config
├── render.yaml                  # Backend service definition
└── README.md
```

---

## Local Development

### Prerequisites

- Python 3.12+
- A [Supabase](https://supabase.com) project (free tier)
- A [Spotify Developer app](https://developer.spotify.com/dashboard) with `http://127.0.0.1:8000/auth/callback` added as a Redirect URI
- A [Ticketmaster API key](https://developer-acct.ticketmaster.com/user/register) (free)
- Any static file server (`python -m http.server`, `npx serve`, VS Code Live Server, etc.)

### 1. Database

Paste the contents of `schema.sql` into your Supabase SQL editor and run it. If you're upgrading an existing database, the `ALTER TABLE` lines at the bottom add the Phase 4 `lat`/`lng` columns safely.

### 2. Backend

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# Edit .env — fill in all values before continuing
```

Generate a `SECRET_KEY`:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Start the API:
```bash
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

The API will be available at `http://127.0.0.1:8000`. Interactive docs at `/docs`.

### 3. Frontend

Serve `frontend/` on `127.0.0.1:3000` (**not** `localhost:3000` — see note below):

```bash
# Python
python -m http.server 3000 --bind 127.0.0.1 --directory frontend

# Node
npx serve frontend -l tcp://127.0.0.1:3000
```

Open `http://127.0.0.1:3000` and click **Connect with Spotify**.

> **Why `127.0.0.1` instead of `localhost`?**
> Browsers treat `localhost` and `127.0.0.1` as different origins. The JWT is sent in the `Authorization` header so there's no cookie issue, but `SPOTIFY_REDIRECT_URI` is registered as `127.0.0.1:8000/auth/callback`. Keeping everything on the same IP avoids mismatches during the OAuth redirect dance.

---

## Deployment

### Backend → Render

`render.yaml` at the project root defines the service. To deploy:

1. Push the repo to GitHub
2. In [Render](https://render.com), create a new **Web Service** and connect your repo
3. Render detects `render.yaml` automatically — confirm the settings
4. In the **Environment** tab, add all variables from the table below
5. Set `SPOTIFY_REDIRECT_URI` to `https://your-service.onrender.com/auth/callback`
6. Set `FRONTEND_URL` to `https://your-app.vercel.app/dashboard.html`
7. Deploy

### Frontend → Vercel

`vercel.json` at the project root handles routing. To deploy:

1. In [Vercel](https://vercel.com), import the GitHub repo
2. Leave all build settings at their defaults — `vercel.json` handles everything
3. Before deploying, update the production `API_BASE` in `frontend/js/api.js`:
   ```js
   : 'https://your-service.onrender.com'  // replace placeholder
   ```
4. Deploy — Vercel serves `frontend/` as a static site

---

## Environment Variables

| Variable | Required | Description |
|----------|:--------:|-------------|
| `SPOTIFY_CLIENT_ID` | ✅ | From the Spotify Developer Dashboard |
| `SPOTIFY_CLIENT_SECRET` | ✅ | From the Spotify Developer Dashboard |
| `SPOTIFY_REDIRECT_URI` | ✅ | `http://127.0.0.1:8000/auth/callback` locally; your Render URL + `/auth/callback` in production |
| `TICKETMASTER_API_KEY` | ✅ | From the Ticketmaster Developer Portal |
| `DATABASE_URL` | ✅ | Supabase URI — **Settings → Database → Connection string (URI)** |
| `SECRET_KEY` | ✅ | 64-char hex string for HS256 JWT signing |
| `FRONTEND_URL` | ✅ | Full URL to `dashboard.html` — used as the post-OAuth redirect target |
| `ENVIRONMENT` | | `development` (default) or `production` |

---

## API Reference

| Method | Path | Auth | Description |
|--------|------|:----:|-------------|
| `GET` | `/auth/login` | — | Redirects to Spotify OAuth consent screen |
| `GET` | `/auth/callback` | — | Handles Spotify callback; issues JWT via redirect to `FRONTEND_URL?token=` |
| `GET` | `/auth/me` | ✅ | Returns the authenticated user's profile |
| `POST` | `/auth/logout` | ✅ | No-op (client clears `localStorage`) |
| `GET` | `/artists` | ✅ | Returns stored top artists with affinity scores |
| `POST` | `/artists/sync` | ✅ | Re-fetches Spotify top artists and recomputes affinity scores |
| `GET` | `/concerts` | ✅ | Returns upcoming shows near the user's city, sorted by affinity; Ticketmaster results cached 6 h |
| `POST` | `/user/city` | ✅ | Geocodes and saves a new city via Nominatim; invalidates concert cache |

Auth endpoints marked ✅ require `Authorization: Bearer <token>` header.

---

## Acknowledgements

- [Spotify Web API](https://developer.spotify.com/documentation/web-api) — listening history and artist data
- [Ticketmaster Discovery API](https://developer.ticketmaster.com/products-and-docs/apis/discovery-api/v2/) — event and venue data
- [OpenStreetMap Nominatim](https://nominatim.openstreetmap.org) — free geocoding
