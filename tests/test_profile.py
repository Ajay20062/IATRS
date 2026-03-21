from fastapi.testclient import TestClient


def signup_candidate(client: TestClient, email: str = "candidate@example.com") -> None:
    response = client.post(
        "/auth/signup/candidate",
        data={
            "full_name": "Candidate User",
            "email": email,
            "phone": "9999999999",
            "password": "secret123",
        },
    )
    assert response.status_code == 201


def signup_recruiter(client: TestClient, email: str = "recruiter@example.com") -> None:
    response = client.post(
        "/auth/signup/recruiter",
        json={
            "full_name": "Recruiter User",
            "email": email,
            "company": "Acme Inc",
            "password": "secret123",
        },
    )
    assert response.status_code == 201


def login(client: TestClient, email: str, password: str = "secret123") -> str:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_profile_requires_auth(client: TestClient) -> None:
    response = client.get("/profile/me")
    assert response.status_code == 401


def test_candidate_profile_fetch_and_update(client: TestClient) -> None:
    signup_candidate(client)
    token = login(client, "candidate@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/profile/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["role"] == "candidate"

    update = client.put(
        "/profile/update",
        headers=headers,
        json={
            "full_name": "Candidate Updated",
            "phone_number": "8888888888",
            "skills": "Python,FastAPI,SQL",
            "bio": "Building ATS systems",
            "education": "B.Tech CSE",
            "experience": "2 years backend",
        },
    )
    assert update.status_code == 200
    payload = update.json()
    assert payload["full_name"] == "Candidate Updated"
    assert payload["skills"] == "Python,FastAPI,SQL"
    assert payload["profile_completion_percentage"] > 0


def test_candidate_uploads_and_resume_analysis(client: TestClient) -> None:
    signup_candidate(client, email="upload-candidate@example.com")
    token = login(client, "upload-candidate@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    image_upload = client.post(
        "/profile/upload-image",
        headers=headers,
        files={"image": ("avatar.png", b"image-bytes", "image/png")},
    )
    assert image_upload.status_code == 200
    assert image_upload.json()["profile_image"]

    resume_upload = client.post(
        "/profile/upload-resume",
        headers=headers,
        files={"resume": ("resume.pdf", b"resume-bytes", "application/pdf")},
    )
    assert resume_upload.status_code == 200
    assert resume_upload.json()["resume_path"]

    analysis = client.post("/profile/analyze-resume", headers=headers)
    assert analysis.status_code == 200
    result = analysis.json()
    assert "resume_score" in result
    assert isinstance(result["extracted_keywords"], list)


def test_recruiter_cannot_update_candidate_fields_or_upload_resume(client: TestClient) -> None:
    signup_recruiter(client)
    token = login(client, "recruiter@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    update = client.put(
        "/profile/update",
        headers=headers,
        json={"skills": "Python"},
    )
    assert update.status_code == 403

    resume_upload = client.post(
        "/profile/upload-resume",
        headers=headers,
        files={"resume": ("resume.pdf", b"resume-bytes", "application/pdf")},
    )
    assert resume_upload.status_code == 403
