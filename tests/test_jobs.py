from tests.conftest import auth_headers, login, signup_recruiter


def test_recruiter_can_create_job(client):
    signup_recruiter(client, "jobs_recruiter@test.com")
    token = login(client, "jobs_recruiter@test.com").json()["access_token"]

    create_response = client.post(
        "/jobs",
        headers=auth_headers(token),
        json={
            "title": "Backend Engineer",
            "department": "Engineering",
            "location": "Chennai",
            "status": "Open",
        },
    )

    assert create_response.status_code == 201
    payload = create_response.json()
    assert payload["title"] == "Backend Engineer"

    list_response = client.get("/jobs")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

