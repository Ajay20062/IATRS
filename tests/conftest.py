import os

import pytest
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = "sqlite:///./test_ats.db"
os.environ["JWT_SECRET_KEY"] = "test-secret"

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.utils.dependencies import get_db  # noqa: E402


def override_get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client():
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def signup_recruiter(client, email="recruiter@test.com"):
    return client.post(
        "/auth/signup/recruiter",
        json={
            "full_name": "Recruiter One",
            "email": email,
            "company": "Acme Inc",
            "password": "strongpass123",
        },
    )


def signup_candidate(client, email="candidate@test.com"):
    return client.post(
        "/auth/signup/candidate",
        data={
            "full_name": "Candidate One",
            "email": email,
            "phone": "9999999999",
            "password": "strongpass123",
        },
    )


def login(client, email, password="strongpass123"):
    return client.post("/auth/login", json={"email": email, "password": password})


def auth_headers(token: str):
    return {"Authorization": f"Bearer {token}"}

