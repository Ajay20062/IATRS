const token = ATS.checkAuth();

const notifications = document.getElementById("notifications");
const profileImagePreview = document.getElementById("profileImagePreview");
const roleLabel = document.getElementById("roleLabel");
const emailLabel = document.getElementById("emailLabel");
const nameLabel = document.getElementById("nameLabel");
const completionBar = document.getElementById("completionBar");
const resumeCard = document.getElementById("resumeCard");
const candidateFields = document.getElementById("candidateFields");
const recruiterFields = document.getElementById("recruiterFields");

function normalizePath(path) {
  if (!path) return "";
  if (/^https?:\/\//i.test(path)) return path;
  return `/${path.replace(/\\/g, "/")}`;
}

function setCompletion(percent) {
  const safe = Number.isFinite(percent) ? Math.max(0, Math.min(100, percent)) : 0;
  completionBar.style.width = `${safe}%`;
  completionBar.textContent = `${safe}%`;
}

function applyProfileToForm(profile) {
  document.getElementById("fullName").value = profile.full_name || "";
  document.getElementById("phoneNumber").value = profile.phone_number || "";
  document.getElementById("bio").value = profile.bio || "";
  document.getElementById("skills").value = profile.skills || "";
  document.getElementById("education").value = profile.education || "";
  document.getElementById("experience").value = profile.experience || "";
  document.getElementById("companyName").value = profile.company_name || "";
  document.getElementById("companyWebsite").value = profile.company_website || "";
  document.getElementById("designation").value = profile.designation || "";
}

async function loadProfile() {
  const profile = await ATS.apiRequest("/profile/me", { token });
  roleLabel.textContent = profile.role;
  emailLabel.textContent = profile.email;
  nameLabel.textContent = profile.full_name;
  setCompletion(profile.profile_completion_percentage || 0);
  applyProfileToForm(profile);
  profileImagePreview.src = profile.profile_image ? normalizePath(profile.profile_image) : "https://via.placeholder.com/110x110?text=User";

  candidateFields.classList.toggle("d-none", profile.role !== "candidate");
  recruiterFields.classList.toggle("d-none", profile.role !== "recruiter");
  resumeCard.classList.toggle("d-none", profile.role !== "candidate");
}

async function loadStats() {
  const stats = await ATS.apiRequest("/profile/stats", { token });
  document.getElementById("applicationsCount").textContent = stats.applications_count;
  document.getElementById("interviewsAttended").textContent = stats.interviews_attended;
  setCompletion(stats.profile_completion_percentage || 0);
}

document.getElementById("profileForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = {
    full_name: document.getElementById("fullName").value.trim() || null,
    phone_number: document.getElementById("phoneNumber").value.trim() || null,
    bio: document.getElementById("bio").value.trim() || null,
    skills: document.getElementById("skills").value.trim() || null,
    education: document.getElementById("education").value.trim() || null,
    experience: document.getElementById("experience").value.trim() || null,
    company_name: document.getElementById("companyName").value.trim() || null,
    company_website: document.getElementById("companyWebsite").value.trim() || null,
    designation: document.getElementById("designation").value.trim() || null
  };

  Object.keys(payload).forEach((key) => payload[key] === null && delete payload[key]);

  try {
    await ATS.apiRequest("/profile/update", { method: "PUT", token, json: payload });
    ATS.notify(notifications, "Profile updated", "success");
    await Promise.all([loadProfile(), loadStats()]);
  } catch (error) {
    ATS.notify(notifications, error.message, "danger");
  }
});

document.getElementById("imageUploadForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const file = document.getElementById("profileImageInput").files[0];
  if (!file) return;
  const formData = new FormData();
  formData.append("image", file);

  try {
    await ATS.apiRequest("/profile/upload-image", {
      method: "POST",
      token,
      body: formData
    });
    ATS.notify(notifications, "Profile image uploaded", "success");
    await loadProfile();
  } catch (error) {
    ATS.notify(notifications, error.message, "danger");
  }
});

const resumeUploadForm = document.getElementById("resumeUploadForm");
if (resumeUploadForm) {
  resumeUploadForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const file = document.getElementById("resumeInput").files[0];
    if (!file) return;
    const formData = new FormData();
    formData.append("resume", file);

    try {
      await ATS.apiRequest("/profile/upload-resume", {
        method: "POST",
        token,
        body: formData
      });
      ATS.notify(notifications, "Resume uploaded", "success");
      await Promise.all([loadProfile(), loadStats()]);
    } catch (error) {
      ATS.notify(notifications, error.message, "danger");
    }
  });
}

const analyzeResumeBtn = document.getElementById("analyzeResumeBtn");
if (analyzeResumeBtn) {
  analyzeResumeBtn.addEventListener("click", async () => {
    try {
      const result = await ATS.apiRequest("/profile/analyze-resume", { method: "POST", token });
      document.getElementById("resumeAnalysis").textContent = `Keywords: ${result.extracted_keywords.join(", ") || "none"}`;
      document.getElementById("resumeScore").textContent = result.resume_score;
      ATS.notify(notifications, "Resume analyzed", "success");
    } catch (error) {
      ATS.notify(notifications, error.message, "danger");
    }
  });
}

async function init() {
  ATS.renderNavbar();
  try {
    await loadProfile();
    await loadStats();
  } catch (error) {
    ATS.notify(notifications, `Unable to load profile: ${error.message}`, "danger");
  }
}

init();
