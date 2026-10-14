// Demo mode: a self-contained stand-in for the backend so the dashboard can be
// explored without a Spotify account. All artists, venues and events below are
// fictional. Scores are computed with the same weighting as backend/artists.py.

const DEMO_CITY = 'Chicago, IL';

const DEMO_USER = {
  id: 'demo',
  spotify_id: 'demo',
  display_name: 'Demo Listener',
  email: null,
  avatar_url: null,
  city: DEMO_CITY,
};

// Each list is a "top artists" window, most-listened first — the shape Spotify returns.
const DEMO_TOP_LISTS = {
  short_term:  ['Velvet Static', 'Marigold Youth', 'The Lowlight Choir', 'Paper Comets', 'Neon Orchard',
                'Saltwater Saints', 'Juniper Wire', 'Tin Lantern', 'Kite Hours', 'Sundial'],
  medium_term: ['Marigold Youth', 'Velvet Static', 'Paper Comets', 'Harbor Lights', 'The Lowlight Choir',
                'Atlas Fawn', 'Neon Orchard', 'Copper Moth', 'Kite Hours', 'Polar Teeth'],
  long_term:   ['Harbor Lights', 'Marigold Youth', 'Copper Moth', 'Atlas Fawn', 'Polar Teeth',
                'Velvet Static', 'Ember & Ash', 'Paper Comets', 'Quiet Parade', 'Sundial'],
};

const DEMO_GENRES = {
  'Velvet Static': ['shoegaze', 'dream pop'],
  'Marigold Youth': ['indie rock'],
  'The Lowlight Choir': ['chamber folk'],
  'Paper Comets': ['bedroom pop'],
  'Neon Orchard': ['synthpop'],
  'Saltwater Saints': ['surf rock'],
  'Juniper Wire': ['alt country'],
  'Tin Lantern': ['math rock'],
  'Kite Hours': ['indie folk'],
  'Sundial': ['ambient'],
  'Harbor Lights': ['indie rock', 'post-punk'],
  'Atlas Fawn': ['art pop'],
  'Copper Moth': ['garage rock'],
  'Polar Teeth': ['post-hardcore'],
  'Ember & Ash': ['singer-songwriter'],
  'Quiet Parade': ['slowcore'],
};

// [artist, event name, venue, days from today, min price, max price]
const DEMO_EVENTS = [
  ['Velvet Static',      'Velvet Static — Haze Tour',          'The Lantern Room',      12,  32, 55],
  ['Marigold Youth',     'Marigold Youth with Kite Hours',     'Riverside Pavilion',    26,  45, 89],
  ['Marigold Youth',     'Marigold Youth (late show)',         'Riverside Pavilion',    27,  45, 89],
  ['Paper Comets',       'Paper Comets: Small Rooms',          'Northside Social Club', 5,   18, 18],
  ['Harbor Lights',      'Harbor Lights 15th Anniversary',     'Lakeshore Amphitheater', 64, 39, 125],
  ['The Lowlight Choir', 'An Evening with The Lowlight Choir', 'St. Cecilia Hall',      41,  28, 40],
  ['Neon Orchard',       'Neon Orchard — Afterglow',           'Warehouse 9',           19,  25, 35],
  ['Atlas Fawn',         'Atlas Fawn Live',                    'The Fulton Theater',    88,  35, 60],
  ['Copper Moth',        'Copper Moth / Polar Teeth',          'Basement East',         9,   15, 15],
  ['Juniper Wire',       'Juniper Wire',                       'Old Town Tavern',       33,  null, null],
  ['Sundial',            'Sundial: Listening Session',         'Planetarium Dome',      120, 22, 22],
];

const _WEIGHTS = { short_term: 3, medium_term: 2, long_term: 1 };
const _LIMIT = 50;
const _MAX_RAW = _LIMIT * 6;

function _slug(name) {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, '-');
}

// Generated abstract "cover art" (gradient + radar rings) so the demo needs no
// third-party images. Deterministic per artist name.
function _demoArtwork(name) {
  let hash = 0;
  for (const ch of name) hash = (hash * 31 + ch.charCodeAt(0)) >>> 0;
  const h1 = hash % 360;
  const h2 = (h1 + 40 + (hash % 80)) % 360;
  const cx = 60 + (hash % 180);
  const cy = 60 + ((hash >>> 8) % 180);
  const rings = [40, 80, 120, 160, 200]
    .map(r => `<circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="rgba(255,255,255,.14)" stroke-width="10"/>`)
    .join('');
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 300">
    <defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="hsl(${h1},65%,50%)"/><stop offset="1" stop-color="hsl(${h2},70%,22%)"/>
    </linearGradient></defs>
    <rect width="300" height="300" fill="url(#g)"/>${rings}
    <circle cx="${cx}" cy="${cy}" r="14" fill="rgba(255,255,255,.55)"/></svg>`;
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}

function _demoArtists() {
  const scores = {};
  for (const [range, names] of Object.entries(DEMO_TOP_LISTS)) {
    names.forEach((name, idx) => {
      scores[name] = (scores[name] || 0) + (_LIMIT - idx) * _WEIGHTS[range];
    });
  }
  return Object.entries(scores)
    .map(([name, raw]) => ({
      artist_id: _slug(name),
      artist_name: name,
      artist_image_url: _demoArtwork(name),
      affinity_score: Math.round((raw / _MAX_RAW) * 10000) / 100,
      genres: DEMO_GENRES[name] || [],
    }))
    .sort((a, b) => b.affinity_score - a.affinity_score);
}

function _demoConcerts() {
  const byName = Object.fromEntries(_demoArtists().map(a => [a.artist_name, a]));
  const today = new Date();
  return DEMO_EVENTS
    .map(([artist, eventName, venue, days, min, max], i) => {
      const date = new Date(today.getFullYear(), today.getMonth(), today.getDate() + days, 20, 0);
      return {
        event_id: `demo-${i}`,
        event_name: eventName,
        venue_name: venue,
        venue_city: DEMO_CITY,
        event_date: date.toISOString(),
        ticket_url: null,
        price_min: min,
        price_max: max,
        ...byName[artist],
      };
    })
    .sort((a, b) => b.affinity_score - a.affinity_score || a.event_date.localeCompare(b.event_date));
}

function _delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function _demoError(message, status = 400) {
  const err = new Error(message);
  err.status = status;
  return err;
}

async function demoFetch(path, options = {}) {
  const method = (options.method || 'GET').toUpperCase();
  const route = `${method} ${path}`;

  switch (route) {
    case 'GET /auth/me':
      return DEMO_USER;
    case 'GET /artists': {
      const artists = _demoArtists();
      return { synced: artists.length, artists };
    }
    case 'POST /artists/sync': {
      await _delay(600);  // feel like a real round-trip
      const artists = _demoArtists();
      return { synced: artists.length, artists };
    }
    case 'GET /concerts': {
      await _delay(250);
      const concerts = _demoConcerts();
      return { total: concerts.length, concerts };
    }
    case 'POST /user/city':
      throw _demoError(`Demo mode uses fixed sample data for ${DEMO_CITY}. Run the backend to search other cities.`);
    case 'POST /auth/logout':
      return { ok: true };
    default:
      throw _demoError(`Not available in demo mode: ${route}`, 404);
  }
}
