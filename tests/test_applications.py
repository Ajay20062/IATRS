from tests.conftest import auth_headers, login, signup_candidate, signup_recruiter


def test_candidate_can_apply_and_recruiter_can_update_status(client):
    signup_recruiter(client, "apps_recruiter@test.com")
    recruiter_token = login(client, "apps_recruiter@test.com").json()["access_token"]

    job_response = client.post(
        "/jobs",
        headers=auth_headers(recruiter_token),
        json={
            "title": "Data Analyst",
            "department": "Analytics",
            "location": "Bengaluru",
            "status": "Open",
        },
    )
    job_id = job_response.json()["job_id"]

    signup_candidate(client, "apps_candidate@test.com")
    candidate_token = login(client, "apps_candidate@test.com").json()["access_token"]

    apply_response = client.post(
        "/applications",
        headers=auth_headers(candidate_token),
        json={"job_id": job_id},
    )
    assert apply_response.status_code == 201
    application_id = apply_response.json()["application_id"]

    recruiter_view = client.get("/applications", headers=auth_headers(recruiter_token))
    assert recruiter_view.status_code == 200
    assert len(recruiter_view.json()) == 1

    update_response = client.put(
        f"/applications/{application_id}/status",
        headers=auth_headers(recruiter_token),
        json={"status": "Interviewing"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "Interviewing"

