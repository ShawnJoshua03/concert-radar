// Set PROD_API_BASE to your deployed backend (e.g. https://concert-radar-api.onrender.com)
// to enable Spotify login in production. Left as null, the hosted site runs in demo mode.
const PROD_API_BASE = null;

const _IS_LOCAL = ['localhost', '127.0.0.1'].includes(window.location.hostname);
const API_BASE = _IS_LOCAL ? 'http://127.0.0.1:8000' : PROD_API_BASE;

// Demo mode serves sample data from demo.js instead of calling the backend.
// It's on when there is no backend to talk to, or when opted into with ?demo.
const DEMO_MODE = (() => {
  try {
    if (new URLSearchParams(window.location.search).has('demo')) sessionStorage.setItem('demo', '1');
    return !API_BASE || sessionStorage.getItem('demo') === '1';
  } catch (_) {
    return !API_BASE;
  }
})();

function exitDemoMode() {
  try { sessionStorage.removeItem('demo'); } catch (_) {}
}

async function apiFetch(path, options = {}) {
  if (DEMO_MODE) return demoFetch(path, options);

  const { headers: extraHeaders, ...rest } = options;
  const headers = { 'Content-Type': 'application/json', ...extraHeaders };
  const token = localStorage.getItem('session_token');
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, { ...rest, headers });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const err = new Error(body.detail || res.statusText);
    err.status = res.status;
    throw err;
  }

  return res.json();
}
