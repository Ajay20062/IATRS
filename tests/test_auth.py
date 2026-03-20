from tests.conftest import login, signup_candidate, signup_recruiter


def test_candidate_signup_and_login(client):
    signup_response = signup_candidate(client, "candidate1@test.com")
    assert signup_response.status_code == 201
    assert signup_response.json()["email"] == "candidate1@test.com"

    login_response = login(client, "candidate1@test.com")
    assert login_response.status_code == 200
    payload = login_response.json()
    assert "access_token" in payload
    assert payload["role"] == "candidate"


def test_recruiter_signup_and_login(client):
    signup_response = signup_recruiter(client, "recruiter1@test.com")
    assert signup_response.status_code == 201
    assert signup_response.json()["email"] == "recruiter1@test.com"

    login_response = login(client, "recruiter1@test.com")
    assert login_response.status_code == 200
    payload = login_response.json()
    assert "access_token" in payload
    assert payload["role"] == "recruiter"

