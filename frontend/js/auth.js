function _extractTokenFromUrl() {
  const params = new URLSearchParams(window.location.search);
  const token = params.get('token');
  if (token) {
    localStorage.setItem('session_token', token);
    window.history.replaceState({}, '', window.location.pathname);
  }
}

async function getUser() {
  try {
    return await apiFetch('/auth/me');
  } catch (err) {
    if (err.status === 401) return null;
    throw err;
  }
}

// Call on dashboard.html — redirects to / if not logged in
async function requireAuth() {
  _extractTokenFromUrl();
  const user = await getUser();
  if (!user) {
    window.location.href = '/';
    return null;
  }
  return user;
}

// Call on index.html — redirects to dashboard if already logged in
async function requireGuest() {
  const user = await getUser();
  if (user) {
    window.location.href = '/dashboard.html';
  }
}

async function logout() {
  localStorage.removeItem('session_token');
  window.location.href = '/';
}
