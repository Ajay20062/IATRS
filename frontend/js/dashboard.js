const token = localStorage.getItem("ats_token");
const role = localStorage.getItem("ats_role");

if (!token) {
  window.location.href = "./login.html";
}

const notifications = document.getElementById("notifications");
const roleLabel = document.getElementById("roleLabel");
const candidateSection = document.getElementById("candidateSection");
const recruiterSection = document.getElementById("recruiterSection");

if (roleLabel) roleLabel.textContent = role || "unknown";

function logout() {
  localStorage.removeItem("ats_token");
  localStorage.removeItem("ats_role");
  window.location.href = "./login.html";
}

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
    const apps = await ATS.apiRequest("/applications", { token });
    const table = document.getElementById("appsTable");
    const rows = apps.length
      ? apps
          .map(
            (app) =>
              `<tr><td>${app.application_id}</td><td>${app.job_title || app.job_id}</td><td>${statusBadge(app.status)}</td><td>${new Date(app.created_at).toLocaleString()}</td></tr>`
          )
          .join("")
      : renderEmptyRow(4, "You have not applied for any jobs yet");
    table.innerHTML = `<thead><tr><th>ID</th><th>Job</th><th>Status</th><th>Date</th></tr></thead><tbody>${rows}</tbody>`;
  } catch (error) {
    ATS.notify(notifications, `Unable to load applications: ${error.message}`, "danger");
  }
}

async function loadMyInterviews() {
  try {
    const interviews = await ATS.apiRequest("/interviews", { token });
    const table = document.getElementById("interviewsTable");
    const rows = interviews.length
      ? interviews
          .map(
            (item) =>
              `<tr><td>${item.interview_id}</td><td>${item.application_id}</td><td>${new Date(item.scheduled_at).toLocaleString()}</td><td>${item.interview_type}</td><td>${statusBadge(item.status)}</td></tr>`
          )
          .join("")
      : renderEmptyRow(5, "No interviews scheduled");
    table.innerHTML = `<thead><tr><th>ID</th><th>Application</th><th>When</th><th>Type</th><th>Status</th></tr></thead><tbody>${rows}</tbody>`;
  } catch (error) {
    ATS.notify(notifications, `Unable to load interviews: ${error.message}`, "danger");
  }
}

async function loadRecruiterApplications() {
  try {
    const apps = await ATS.apiRequest("/applications", { token });
    const table = document.getElementById("recruiterAppsTable");
    const rows = apps.length
      ? apps
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
      : renderEmptyRow(5, "No applications yet");
    table.innerHTML = `<thead><tr><th>ID</th><th>Candidate</th><th>Job</th><th>Status</th><th>Update</th></tr></thead><tbody>${rows}</tbody>`;
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

async function loadRecruiterInterviews() {
  try {
    const interviews = await ATS.apiRequest("/interviews", { token });
    const table = document.getElementById("recruiterInterviewsTable");
    const rows = interviews.length
      ? interviews
          .map(
            (item) =>
              `<tr><td>${item.interview_id}</td><td>${item.application_id}</td><td>${new Date(item.scheduled_at).toLocaleString()}</td><td>${item.interview_type}</td><td>${statusBadge(item.status)}</td></tr>`
          )
          .join("")
      : renderEmptyRow(5, "No interviews scheduled");
    table.innerHTML = `<thead><tr><th>ID</th><th>Application</th><th>Date & Time</th><th>Type</th><th>Status</th></tr></thead><tbody>${rows}</tbody>`;
  } catch (error) {
    ATS.notify(notifications, `Unable to load recruiter interviews: ${error.message}`, "danger");
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
      await loadRecruiterInterviews();
    } catch (error) {
      ATS.notify(notifications, error.message, "danger");
    }
  });
}

async function init() {
  if (role === "candidate") {
    candidateSection.classList.remove("d-none");
    await loadJobs();
    await loadMyApplications();
    await loadMyInterviews();
    return;
  }

  if (role === "recruiter") {
    recruiterSection.classList.remove("d-none");
    await loadRecruiterApplications();
    await loadRecruiterInterviews();
    return;
  }

  ATS.notify(notifications, "Unknown role. Please login again.", "danger");
  localStorage.removeItem("ats_token");
  localStorage.removeItem("ats_role");
  window.setTimeout(() => {
    window.location.href = "./login.html";
  }, 1200);
}

window.logout = logout;
window.loadJobs = loadJobs;
window.applyJob = applyJob;
window.updateApplicationStatus = updateApplicationStatus;

init();

