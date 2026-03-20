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

  window.ATS = ATS;
})();

