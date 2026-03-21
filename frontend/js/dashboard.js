const token = ATS.checkAuth();
const role = localStorage.getItem("ats_role");

const notifications = document.getElementById("notifications");
const roleLabel = document.getElementById("roleLabel");
const candidateSection = document.getElementById("candidateSection");
const recruiterSection = document.getElementById("recruiterSection");
const summaryCards = document.getElementById("summaryCards");
const refreshBtn = document.getElementById("refreshBtn");
const autoRefreshToggle = document.getElementById("autoRefreshToggle");
const candidateAppStatusFilter = document.getElementById("candidateAppStatusFilter");
const recruiterAppStatusFilter = document.getElementById("recruiterAppStatusFilter");
const recruiterAppSearch = document.getElementById("recruiterAppSearch");

if (roleLabel) roleLabel.textContent = role || "unknown";

let currentUser = null;
let autoRefreshTimer = null;
let openJobsCache = [];
let candidateAppsCache = [];
let candidateInterviewsCache = [];
let recruiterJobsCache = [];
let recruiterAppsCache = [];
let recruiterInterviewsCache = [];

function statusBadge(status) {
  const map = {
    Applied: "secondary",
    Screening: "primary",
    Interviewing: "warning",
    Rejected: "danger",
    Hired: "success",
    Scheduled: "info",
    Completed: "success",
    Cancelled: "danger",
    "No-Show": "dark"
  };
  return `<span class="badge badge-status text-bg-${map[status] || "secondary"}">${status}</span>`;
}

function renderEmptyRow(columns, text = "No data found") {
  return `<tr><td colspan="${columns}" class="text-center text-muted py-3">${text}</td></tr>`;
}

function formatDate(dateString) {
  const date = new Date(dateString);
  if (Number.isNaN(date.getTime())) return "-";
  return date.toLocaleString();
}

function isSameDay(left, right) {
  return (
    left.getFullYear() === right.getFullYear() &&
    left.getMonth() === right.getMonth() &&
    left.getDate() === right.getDate()
  );
}

function getRelativeTimeLabel(dateString) {
  const target = new Date(dateString);
  if (Number.isNaN(target.getTime())) return "";
  const diffMs = target.getTime() - Date.now();
  const diffMin = Math.round(diffMs / 60000);
  if (Math.abs(diffMin) < 60) return `${diffMin}m`;
  const diffHr = Math.round(diffMin / 60);
  if (Math.abs(diffHr) < 24) return `${diffHr}h`;
  return `${Math.round(diffHr / 24)}d`;
}

function renderSummary(items) {
  if (!summaryCards) return;
  const html = items
    .map(
      (item) => `
      <div class="col-12 col-md-4">
        <div class="summary-card">
          <p class="summary-label">${item.label}</p>
          <p class="summary-value">${item.value}</p>
        </div>
      </div>`
    )
    .join("");
  summaryCards.innerHTML = html;
}

function updateSummary() {
  if (role === "candidate") {
    const upcomingInterviews = candidateInterviewsCache.filter(
      (item) => item.status === "Scheduled" && new Date(item.scheduled_at).getTime() > Date.now()
    ).length;

    renderSummary([
      { label: "Open Jobs", value: openJobsCache.length },
      { label: "Applications Sent", value: candidateAppsCache.length },
      { label: "Upcoming Interviews", value: upcomingInterviews }
    ]);
    return;
  }

  if (role === "recruiter") {
    const activeJobs = recruiterJobsCache.filter((job) => job.status === "Open").length;
    const today = new Date();
    const interviewsToday = recruiterInterviewsCache.filter((item) =>
      isSameDay(new Date(item.scheduled_at), today)
    ).length;

    renderSummary([
      { label: "Active Jobs", value: activeJobs },
      { label: "Total Applications", value: recruiterAppsCache.length },
      { label: "Interviews Today", value: interviewsToday }
    ]);
  }
}

function renderCandidateApplications() {
  const table = document.getElementById("appsTable");
  if (!table) return;

  const statusFilter = candidateAppStatusFilter ? candidateAppStatusFilter.value : "all";
  const filteredApps =
    statusFilter === "all"
      ? candidateAppsCache
      : candidateAppsCache.filter((app) => app.status === statusFilter);

  const rows = filteredApps.length
    ? filteredApps
        .map(
          (app) =>
            `<tr><td>${app.application_id}</td><td>${app.job_title || app.job_id}</td><td>${statusBadge(app.status)}</td><td>${formatDate(app.created_at)}</td></tr>`
        )
        .join("")
    : renderEmptyRow(4, "No applications match this filter");
  table.innerHTML = `<thead><tr><th>ID</th><th>Job</th><th>Status</th><th>Date</th></tr></thead><tbody>${rows}</tbody>`;
}

function renderRecruiterApplications() {
  const table = document.getElementById("recruiterAppsTable");
  if (!table) return;

  const statusFilter = recruiterAppStatusFilter ? recruiterAppStatusFilter.value : "all";
  const searchValue = recruiterAppSearch ? recruiterAppSearch.value.trim().toLowerCase() : "";

  const filteredApps = recruiterAppsCache.filter((app) => {
    if (statusFilter !== "all" && app.status !== statusFilter) return false;
    if (!searchValue) return true;
    const candidate = (app.candidate_name || "").toLowerCase();
    const job = (app.job_title || "").toLowerCase();
    return candidate.includes(searchValue) || job.includes(searchValue);
  });

  const rows = filteredApps.length
    ? filteredApps
        .map(
          (app) => `<tr><td>${app.application_id}</td><td>${app.candidate_name || app.candidate_id}</td><td>${app.job_title || app.job_id}</td><td>${statusBadge(app.status)}</td><td>
      <select class="form-select form-select-sm" onchange="updateApplicationStatus(${app.application_id}, this.value)">
      <option ${app.status === "Applied" ? "selected" : ""}>Applied</option>
      <option ${app.status === "Screening" ? "selected" : ""}>Screening</option>
      <option ${app.status === "Interviewing" ? "selected" : ""}>Interviewing</option>
      <option ${app.status === "Rejected" ? "selected" : ""}>Rejected</option>
      <option ${app.status === "Hired" ? "selected" : ""}>Hired</option>
      </select></td></tr>`
        )
        .join("")
    : renderEmptyRow(5, "No applications match this filter");
  table.innerHTML = `<thead><tr><th>ID</th><th>Candidate</th><th>Job</th><th>Status</th><th>Update</th></tr></thead><tbody>${rows}</tbody>`;
}

function renderCandidateInterviews() {
  const table = document.getElementById("interviewsTable");
  if (!table) return;

  const rows = candidateInterviewsCache.length
    ? candidateInterviewsCache
        .map((item) => {
          const relative = getRelativeTimeLabel(item.scheduled_at);
          return `<tr><td>${item.interview_id}</td><td>${item.application_id}</td><td>${formatDate(item.scheduled_at)}${relative ? ` <span class="text-muted small">(${relative})</span>` : ""}</td><td>${item.interview_type}</td><td>${statusBadge(item.status)}</td></tr>`;
        })
        .join("")
    : renderEmptyRow(5, "No interviews scheduled");
  table.innerHTML = `<thead><tr><th>ID</th><th>Application</th><th>When</th><th>Type</th><th>Status</th></tr></thead><tbody>${rows}</tbody>`;
}

function renderRecruiterInterviews() {
  const table = document.getElementById("recruiterInterviewsTable");
  if (!table) return;

  const rows = recruiterInterviewsCache.length
    ? recruiterInterviewsCache
        .map((item) => {
          const relative = getRelativeTimeLabel(item.scheduled_at);
          return `<tr><td>${item.interview_id}</td><td>${item.application_id}</td><td>${formatDate(item.scheduled_at)}${relative ? ` <span class="text-muted small">(${relative})</span>` : ""}</td><td>${item.interview_type}</td><td>${statusBadge(item.status)}</td><td>
          <select class="form-select form-select-sm" onchange="updateInterviewStatus(${item.interview_id}, this.value)">
            <option ${item.status === "Scheduled" ? "selected" : ""}>Scheduled</option>
            <option ${item.status === "Completed" ? "selected" : ""}>Completed</option>
            <option ${item.status === "Cancelled" ? "selected" : ""}>Cancelled</option>
            <option ${item.status === "No-Show" ? "selected" : ""}>No-Show</option>
          </select>
          </td></tr>`;
        })
        .join("")
    : renderEmptyRow(6, "No interviews scheduled");
  table.innerHTML = `<thead><tr><th>ID</th><th>Application</th><th>Date & Time</th><th>Type</th><th>Status</th><th>Update</th></tr></thead><tbody>${rows}</tbody>`;
}

function renderRecruiterJobs() {
  const table = document.getElementById("recruiterJobsTable");
  if (!table) return;

  const rows = recruiterJobsCache.length
    ? recruiterJobsCache
        .map(
          (job) => `<tr><td>${job.job_id}</td><td>${job.title}</td><td>${job.department}</td><td>${job.location}</td><td>
            <select class="form-select form-select-sm" onchange="updateJobStatus(${job.job_id}, this.value)">
              <option ${job.status === "Open" ? "selected" : ""}>Open</option>
              <option ${job.status === "Paused" ? "selected" : ""}>Paused</option>
              <option ${job.status === "Closed" ? "selected" : ""}>Closed</option>
            </select>
          </td><td><button class="btn btn-outline-danger btn-sm" onclick="deleteJob(${job.job_id})">Delete</button></td></tr>`
        )
        .join("")
    : renderEmptyRow(6, "No jobs posted yet");
  table.innerHTML = `<thead><tr><th>ID</th><th>Title</th><th>Department</th><th>Location</th><th>Status</th><th>Action</th></tr></thead><tbody>${rows}</tbody>`;
}

async function loadCurrentUser() {
  try {
    currentUser = await ATS.apiRequest("/auth/me", { token });
    if (roleLabel) {
      roleLabel.textContent = `${currentUser.role} • ${currentUser.full_name}`;
    }
  } catch (error) {
    ATS.notify(notifications, `Unable to load profile: ${error.message}`, "danger");
  }
}

async function loadJobs() {
  try {
    const params = new URLSearchParams();
    const title = document.getElementById("searchTitle").value.trim();
    const location = document.getElementById("searchLocation").value.trim();
    const department = document.getElementById("searchDept").value.trim();
    if (title) params.append("search", title);
    if (location) params.append("location", location);
    if (department) params.append("department", department);
    params.append("status", "Open");

    const jobs = await ATS.apiRequest(`/jobs?${params.toString()}`, { token });
    openJobsCache = jobs;
    const table = document.getElementById("jobsTable");
    const rows = jobs.length
      ? jobs
          .map(
            (job) =>
              `<tr><td>${job.job_id}</td><td>${job.title}</td><td>${job.department}</td><td>${job.location}</td><td><button class="btn btn-sm btn-primary" onclick="applyJob(${job.job_id})">Apply</button></td></tr>`
          )
          .join("")
      : renderEmptyRow(5, "No open jobs for this filter");

    table.innerHTML = `<thead><tr><th>ID</th><th>Title</th><th>Department</th><th>Location</th><th>Action</th></tr></thead><tbody>${rows}</tbody>`;
    updateSummary();
  } catch (error) {
    ATS.notify(notifications, `Unable to load jobs: ${error.message}`, "danger");
  }
}

async function applyJob(jobId) {
  try {
    await ATS.apiRequest("/applications", {
      method: "POST",
      token,
      json: { job_id: jobId }
    });
    ATS.notify(notifications, "Application submitted", "success");
    await loadMyApplications();
  } catch (error) {
    ATS.notify(notifications, error.message, "danger");
  }
}

async function loadMyApplications() {
  try {
    candidateAppsCache = await ATS.apiRequest("/applications", { token });
    renderCandidateApplications();
    updateSummary();
  } catch (error) {
    ATS.notify(notifications, `Unable to load applications: ${error.message}`, "danger");
  }
}

async function loadMyInterviews() {
  try {
    candidateInterviewsCache = await ATS.apiRequest("/interviews", { token });
    renderCandidateInterviews();
    updateSummary();
  } catch (error) {
    ATS.notify(notifications, `Unable to load interviews: ${error.message}`, "danger");
  }
}

async function loadRecruiterApplications() {
  try {
    recruiterAppsCache = await ATS.apiRequest("/applications", { token });
    renderRecruiterApplications();
    updateSummary();
  } catch (error) {
    ATS.notify(notifications, `Unable to load recruiter applications: ${error.message}`, "danger");
  }
}

async function updateApplicationStatus(id, status) {
  try {
    await ATS.apiRequest(`/applications/${id}/status`, {
      method: "PUT",
      token,
      json: { status }
    });
    ATS.notify(notifications, "Application status updated", "success");
    await loadRecruiterApplications();
  } catch (error) {
    ATS.notify(notifications, error.message, "danger");
  }
}

async function loadRecruiterJobs() {
  try {
    const jobs = await ATS.apiRequest("/jobs", { token });
    if (currentUser && typeof currentUser.recruiter_id === "number") {
      recruiterJobsCache = jobs.filter((job) => job.recruiter_id === currentUser.recruiter_id);
    } else {
      recruiterJobsCache = jobs;
    }
    renderRecruiterJobs();
    updateSummary();
  } catch (error) {
    ATS.notify(notifications, `Unable to load jobs: ${error.message}`, "danger");
  }
}

async function updateJobStatus(jobId, status) {
  const target = recruiterJobsCache.find((item) => item.job_id === jobId);
  if (!target) return;
  try {
    await ATS.apiRequest(`/jobs/${jobId}`, {
      method: "PUT",
      token,
      json: {
        title: target.title,
        department: target.department,
        location: target.location,
        status
      }
    });
    ATS.notify(notifications, "Job status updated", "success");
    await loadRecruiterJobs();
  } catch (error) {
    ATS.notify(notifications, error.message, "danger");
    await loadRecruiterJobs();
  }
}

async function deleteJob(jobId) {
  const confirmed = window.confirm(`Delete job #${jobId}? This also removes linked applications.`);
  if (!confirmed) return;
  try {
    await ATS.apiRequest(`/jobs/${jobId}`, {
      method: "DELETE",
      token
    });
    ATS.notify(notifications, "Job deleted", "success");
    await Promise.all([loadRecruiterJobs(), loadRecruiterApplications(), loadRecruiterInterviews()]);
  } catch (error) {
    ATS.notify(notifications, error.message, "danger");
  }
}

async function loadRecruiterInterviews() {
  try {
    recruiterInterviewsCache = await ATS.apiRequest("/interviews", { token });
    renderRecruiterInterviews();
    updateSummary();
  } catch (error) {
    ATS.notify(notifications, `Unable to load recruiter interviews: ${error.message}`, "danger");
  }
}

async function updateInterviewStatus(interviewId, status) {
  try {
    await ATS.apiRequest(`/interviews/${interviewId}`, {
      method: "PUT",
      token,
      json: { status }
    });
    ATS.notify(notifications, "Interview updated", "success");
    await loadRecruiterInterviews();
  } catch (error) {
    ATS.notify(notifications, error.message, "danger");
    await loadRecruiterInterviews();
  }
}

async function refreshDashboard() {
  if (role === "candidate") {
    await Promise.all([loadJobs(), loadMyApplications(), loadMyInterviews()]);
    return;
  }
  if (role === "recruiter") {
    await Promise.all([loadRecruiterJobs(), loadRecruiterApplications(), loadRecruiterInterviews()]);
  }
}

const jobForm = document.getElementById("jobForm");
if (jobForm) {
  jobForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = {
      title: document.getElementById("jobTitle").value.trim(),
      department: document.getElementById("jobDept").value.trim(),
      location: document.getElementById("jobLoc").value.trim(),
      status: document.getElementById("jobStatus").value
    };

    try {
      await ATS.apiRequest("/jobs", {
        method: "POST",
        token,
        json: payload
      });
      ATS.notify(notifications, "Job posted successfully", "success");
      jobForm.reset();
      await loadRecruiterJobs();
    } catch (error) {
      ATS.notify(notifications, error.message, "danger");
    }
  });
}

const interviewForm = document.getElementById("interviewForm");
if (interviewForm) {
  interviewForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const rawDate = document.getElementById("scheduledAt").value;
    const payload = {
      application_id: Number(document.getElementById("applicationId").value),
      scheduled_at: new Date(rawDate).toISOString(),
      interview_type: document.getElementById("interviewType").value,
      status: "Scheduled"
    };

    try {
      await ATS.apiRequest("/interviews", {
        method: "POST",
        token,
        json: payload
      });
      ATS.notify(notifications, "Interview scheduled", "success");
      interviewForm.reset();
      await Promise.all([loadRecruiterInterviews(), loadRecruiterApplications()]);
    } catch (error) {
      ATS.notify(notifications, error.message, "danger");
    }
  });
}

async function init() {
  ATS.renderNavbar();
  await loadCurrentUser();

  if (refreshBtn) {
    refreshBtn.addEventListener("click", async () => {
      await refreshDashboard();
      ATS.notify(notifications, "Dashboard refreshed", "info");
    });
  }

  if (autoRefreshToggle) {
    autoRefreshToggle.addEventListener("change", (event) => {
      if (autoRefreshTimer) {
        window.clearInterval(autoRefreshTimer);
        autoRefreshTimer = null;
      }
      if (event.target.checked) {
        autoRefreshTimer = window.setInterval(() => {
          refreshDashboard();
        }, 30000);
      }
    });
  }

  if (candidateAppStatusFilter) {
    candidateAppStatusFilter.addEventListener("change", renderCandidateApplications);
  }

  if (recruiterAppStatusFilter) {
    recruiterAppStatusFilter.addEventListener("change", renderRecruiterApplications);
  }

  if (recruiterAppSearch) {
    recruiterAppSearch.addEventListener("input", renderRecruiterApplications);
  }

  if (role === "candidate") {
    candidateSection.classList.remove("d-none");
    await refreshDashboard();
    return;
  }

  if (role === "recruiter") {
    recruiterSection.classList.remove("d-none");
    await refreshDashboard();
    return;
  }

  ATS.notify(notifications, "Unknown role. Please login again.", "danger");
  localStorage.removeItem("ats_token");
  localStorage.removeItem("ats_role");
  window.setTimeout(() => {
    window.location.href = "./login.html";
  }, 1200);
}

window.loadJobs = loadJobs;
window.applyJob = applyJob;
window.updateApplicationStatus = updateApplicationStatus;
window.updateInterviewStatus = updateInterviewStatus;
window.updateJobStatus = updateJobStatus;
window.deleteJob = deleteJob;

init();
