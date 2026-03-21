(function () {
  const ATS = {};

  ATS.resolveApiBase = function resolveApiBase() {
    if (window.location.protocol === "file:") return "http://127.0.0.1:8000";

    const host = window.location.hostname;
    const port = window.location.port;
    if (port === "63342") return "http://127.0.0.1:8000";

    if (host === "localhost" || host === "127.0.0.1") {
      return `${window.location.protocol}//${host}${port ? `:${port}` : ""}`;
    }
    return window.location.origin;
  };

  ATS.renderMessage = function renderMessage(element, text, type = "info") {
    if (!element) return;
    element.className = `small mt-3 text-${type}`;
    element.textContent = text;
  };

  ATS.notify = function notify(container, text, type = "info") {
    if (!container) return;
    container.innerHTML = `<div class="alert alert-${type} py-2 mb-3">${text}</div>`;
    window.setTimeout(() => {
      container.innerHTML = "";
    }, 3000);
  };

  ATS.apiRequest = async function apiRequest(path, options = {}) {
    const {
      method = "GET",
      token = null,
      json = null,
      body = null,
      headers = {},
      timeoutMs = 10000,
      baseUrl = ATS.resolveApiBase()
    } = options;

    const requestHeaders = { ...headers };
    if (token) requestHeaders.Authorization = `Bearer ${token}`;
    if (json !== null) requestHeaders["Content-Type"] = "application/json";

    const controller = new AbortController();
    const timer = window.setTimeout(() => controller.abort(), timeoutMs);

    try {
      const response = await fetch(`${baseUrl}${path}`, {
        method,
        headers: requestHeaders,
        body: json !== null ? JSON.stringify(json) : body,
        signal: controller.signal
      });

      const contentType = response.headers.get("content-type") || "";
      const payload = contentType.includes("application/json")
        ? await response.json()
        : await response.text();

      if (!response.ok) {
        if (response.status === 401) {
          ATS.logout();
        }
        const message =
          (payload && payload.detail) ||
          (payload && payload.error) ||
          (typeof payload === "string" && payload) ||
          `Request failed (${response.status})`;
        const error = new Error(message);
        error.status = response.status;
        throw error;
      }

      return payload;
    } finally {
      window.clearTimeout(timer);
    }
  };

  ATS.checkAuth = function checkAuth() {
    const token = localStorage.getItem("ats_token");
    if (!token) {
      window.location.href = "./login.html";
      return null;
    }
    return token;
  };

  ATS.logout = function logout() {
    localStorage.removeItem("ats_token");
    localStorage.removeItem("ats_role");
    window.location.href = "./login.html";
  };

  ATS.renderNavbar = function renderNavbar(containerId = "navbar-placeholder") {
    const container = document.getElementById(containerId);
    if (!container) return;

    const role = localStorage.getItem("ats_role");
    
    let links = "";
    if (role) {
      links = `
        <span class="badge bg-light text-dark me-2 border">${role.toUpperCase()}</span>
        <a class="btn btn-outline-light btn-sm" href="./dashboard.html">Dashboard</a>
        <a class="btn btn-outline-light btn-sm" href="./profile.html">Profile</a>
        <button class="btn btn-outline-danger btn-sm" onclick="ATS.logout()">Logout</button>
      `;
    } else {
      links = `
        <a class="btn btn-outline-light btn-sm" href="./login.html">Login</a>
        <a class="btn btn-light btn-sm" href="./signup.html">Sign Up</a>
      `;
    }

    container.innerHTML = `
      <nav class="navbar navbar-expand-lg app-navbar mb-4">
        <div class="container">
          <a class="navbar-brand fw-bold" href="./index.html">ATS Workspace</a>
          <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
            <span class="navbar-toggler-icon"></span>
          </button>
          <div class="collapse navbar-collapse justify-content-end" id="navbarNav">
            <div class="d-flex gap-2 align-items-center">
              ${links}
            </div>
          </div>
        </div>
      </nav>
    `;
  };

  window.ATS = ATS;
})();

