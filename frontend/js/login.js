const loginForm = document.getElementById("loginForm");
const messageBox = document.getElementById("msg");
const submitButton = loginForm ? loginForm.querySelector("button[type='submit']") : null;

if (localStorage.getItem("ats_token")) {
  window.location.href = "./dashboard.html";
}

if (loginForm) {
  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!submitButton) return;

    submitButton.disabled = true;
    submitButton.textContent = "Logging in...";
    ATS.renderMessage(messageBox, "Authenticating account...", "muted");

    try {
      const payload = {
        email: document.getElementById("email").value.trim(),
        password: document.getElementById("password").value
      };

      const data = await ATS.apiRequest("/auth/login", {
        method: "POST",
        json: payload
      });

      localStorage.setItem("ats_token", data.access_token);
      localStorage.setItem("ats_role", data.role);
      window.location.href = "./dashboard.html";
    } catch (error) {
      ATS.renderMessage(messageBox, error.message, "danger");
      submitButton.disabled = false;
      submitButton.textContent = "Login";
    }
  });
}

