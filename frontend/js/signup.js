const signupMessage = document.getElementById("msg");
const candidateForm = document.getElementById("candidateForm");
const recruiterForm = document.getElementById("recruiterForm");

function setFormLoading(button, isLoading, label) {
  if (!button) return;
  button.disabled = isLoading;
  button.textContent = isLoading ? "Please wait..." : label;
}

if (candidateForm) {
  const candidateSubmit = candidateForm.querySelector("button[type='submit']");
  candidateForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    setFormLoading(candidateSubmit, true, "Signup as Candidate");
    ATS.renderMessage(signupMessage, "Creating candidate account...", "muted");

    try {
      const formData = new FormData();
      formData.append("full_name", document.getElementById("c_name").value.trim());
      formData.append("email", document.getElementById("c_email").value.trim());
      formData.append("phone", document.getElementById("c_phone").value.trim());
      formData.append("password", document.getElementById("c_password").value);
      const resumeFile = document.getElementById("c_resume").files[0];
      if (resumeFile) formData.append("resume", resumeFile);

      await ATS.apiRequest("/auth/signup/candidate", {
        method: "POST",
        body: formData
      });

      candidateForm.reset();
      ATS.renderMessage(signupMessage, "Candidate signup successful. You can login now.", "success");
    } catch (error) {
      ATS.renderMessage(signupMessage, error.message, "danger");
    } finally {
      setFormLoading(candidateSubmit, false, "Signup as Candidate");
    }
  });
}

if (recruiterForm) {
  const recruiterSubmit = recruiterForm.querySelector("button[type='submit']");
  recruiterForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    setFormLoading(recruiterSubmit, true, "Signup as Recruiter");
    ATS.renderMessage(signupMessage, "Creating recruiter account...", "muted");

    try {
      const payload = {
        full_name: document.getElementById("r_name").value.trim(),
        email: document.getElementById("r_email").value.trim(),
        company: document.getElementById("r_company").value.trim(),
        password: document.getElementById("r_password").value
      };

      await ATS.apiRequest("/auth/signup/recruiter", {
        method: "POST",
        json: payload
      });

      recruiterForm.reset();
      ATS.renderMessage(signupMessage, "Recruiter signup successful. You can login now.", "success");
    } catch (error) {
      ATS.renderMessage(signupMessage, error.message, "danger");
    } finally {
      setFormLoading(recruiterSubmit, false, "Signup as Recruiter");
    }
  });
}

