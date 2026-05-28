const API_BASE = "http://127.0.0.1:8000";

function getAccessToken() {
    return localStorage.getItem("access_token");
}

function getRefreshToken() {
    return localStorage.getItem("refresh_token");
}

function setTokens(accessToken, refreshToken) {
    localStorage.setItem("access_token", accessToken);
    if (refreshToken) {
        localStorage.setItem("refresh_token", refreshToken);
    }
}

function setUser(user) {
    if (user) {
        localStorage.setItem("user", JSON.stringify(user));
    }
}

function getUser() {
    const raw = localStorage.getItem("user");
    return raw ? JSON.parse(raw) : null;
}

function clearAuth() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user");
}

function requireAuth() {
    if (!getAccessToken()) {
        window.location.href = "login.html";
    }
}

function redirectIfLoggedIn() {
    if (getAccessToken()) {
        window.location.href = "dashboard.html";
    }
}

async function parseResponse(res) {
    const data = await res.json().catch(() => ({}));
    if (!res.ok && !data.message) {
        data.message = "Request failed";
    }
    return data;
}

async function apiPost(path, body, useAuth = false) {
    const headers = { "Content-Type": "application/json" };
    if (useAuth) {
        const token = getAccessToken();
        if (token) {
            headers.Authorization = `Bearer ${token}`;
        }
    }

    const res = await fetch(`${API_BASE}${path}`, {
        method: "POST",
        headers,
        body: JSON.stringify(body),
    });

    return parseResponse(res);
}

async function apiGet(path, useAuth = true) {
    const headers = {};
    if (useAuth) {
        const token = getAccessToken();
        if (token) {
            headers.Authorization = `Bearer ${token}`;
        }
    }

    const res = await fetch(`${API_BASE}${path}`, { headers });
    return parseResponse(res);
}

async function refreshAccessToken() {
    const refreshToken = getRefreshToken();
    if (!refreshToken) {
        return false;
    }

    const res = await fetch(
        `${API_BASE}/refresh?refresh_token=${encodeURIComponent(refreshToken)}`,
        { method: "POST" }
    );
    const data = await parseResponse(res);

    if (data.access_token) {
        localStorage.setItem("access_token", data.access_token);
        return true;
    }

    return false;
}

async function apiGetWithRefresh(path) {
    let data = await apiGet(path, true);

    if (
        data.message &&
        (data.message.includes("Invalid") ||
            data.message.includes("expired") ||
            data.message.includes("logged out"))
    ) {
        const refreshed = await refreshAccessToken();
        if (refreshed) {
            data = await apiGet(path, true);
        }
    }

    return data;
}

function showMessage(el, text, isError) {
    if (!el) return;
    el.textContent = text;
    el.className = isError ? "message error" : "message success";
    el.hidden = !text;
}
