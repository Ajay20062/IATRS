"""
Comprehensive unit tests for IATRS API.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.utils.security import hash_password

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_iatrs.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create test client with database override."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ============ Authentication Tests ============

class TestAuthentication:
    """Test authentication endpoints."""
    
    def test_signup_candidate(self, client: TestClient, db_session):
        """Test candidate signup."""
        response = client.post(
            "/auth/signup/candidate",
            data={
                "full_name": "Test Candidate",
                "email": "candidate@test.com",
                "phone": "1234567890",
                "password": "SecurePass123!",
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "candidate@test.com"
        assert "candidate_id" in data
    
    def test_signup_recruiter(self, client: TestClient, db_session):
        """Test recruiter signup."""
        response = client.post(
            "/auth/signup/recruiter",
            json={
                "full_name": "Test Recruiter",
                "email": "recruiter@test.com",
                "company": "Test Company",
                "password": "SecurePass123!",
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "recruiter@test.com"
        assert "recruiter_id" in data
    
    def test_login_success(self, client: TestClient, db_session):
        """Test successful login."""
        # Create user first
        client.post(
            "/auth/signup/candidate",
            data={
                "full_name": "Login Test",
                "email": "login@test.com",
                "phone": "1234567890",
                "password": "SecurePass123!",
            }
        )
        
        # Login
        response = client.post(
            "/auth/login",
            json={
                "email": "login@test.com",
                "password": "SecurePass123!",
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["role"] == "candidate"
    
    def test_login_wrong_password(self, client: TestClient, db_session):
        """Test login with wrong password."""
        # Create user first
        client.post(
            "/auth/signup/candidate",
            data={
                "full_name": "Login Test",
                "email": "login@test.com",
                "phone": "1234567890",
                "password": "SecurePass123!",
            }
        )
        
        # Login with wrong password
        response = client.post(
            "/auth/login",
            json={
                "email": "login@test.com",
                "password": "WrongPassword!",
            }
        )
        assert response.status_code == 401
    
    def test_duplicate_email_signup(self, client: TestClient, db_session):
        """Test signup with duplicate email."""
        # First signup
        client.post(
            "/auth/signup/candidate",
            data={
                "full_name": "First User",
                "email": "duplicate@test.com",
                "phone": "1234567890",
                "password": "SecurePass123!",
            }
        )
        
        # Second signup with same email
        response = client.post(
            "/auth/signup/candidate",
            data={
                "full_name": "Second User",
                "email": "duplicate@test.com",
                "phone": "1234567891",
                "password": "SecurePass123!",
            }
        )
        assert response.status_code == 400


# ============ Job Tests ============

class TestJobs:
    """Test job management endpoints."""
    
    @pytest.fixture
    def recruiter_token(self, client: TestClient, db_session):
        """Get authenticated recruiter token."""
        # Create recruiter
        client.post(
            "/auth/signup/recruiter",
            json={
                "full_name": "Test Recruiter",
                "email": "recruiter@test.com",
                "company": "Test Company",
                "password": "SecurePass123!",
            }
        )
        
        # Login
        response = client.post(
            "/auth/login",
            json={
                "email": "recruiter@test.com",
                "password": "SecurePass123!",
            }
        )
        return response.json()["access_token"]
    
    def test_create_job(self, client: TestClient, recruiter_token: str):
        """Test job creation."""
        response = client.post(
            "/jobs",
            json={
                "title": "Software Engineer",
                "department": "Engineering",
                "location": "San Francisco",
                "status": "Open",
            },
            headers={"Authorization": f"Bearer {recruiter_token}"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Software Engineer"
        assert "job_id" in data
    
    def test_get_jobs(self, client: TestClient, recruiter_token: str):
        """Test getting all jobs."""
        # Create a job first
        client.post(
            "/jobs",
            json={
                "title": "Software Engineer",
                "department": "Engineering",
                "location": "San Francisco",
                "status": "Open",
            },
            headers={"Authorization": f"Bearer {recruiter_token}"}
        )
        
        # Get jobs
        response = client.get("/jobs")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
    
    def test_search_jobs(self, client: TestClient, recruiter_token: str):
        """Test job search."""
        # Create jobs
        client.post(
            "/jobs",
            json={
                "title": "Python Developer",
                "department": "Engineering",
                "location": "New York",
                "status": "Open",
            },
            headers={"Authorization": f"Bearer {recruiter_token}"}
        )
        
        # Search
        response = client.get("/jobs?search=Python")
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert "Python" in data[0]["title"]
    
    def test_update_job(self, client: TestClient, recruiter_token: str):
        """Test job update."""
        # Create job
        create_response = client.post(
            "/jobs",
            json={
                "title": "Software Engineer",
                "department": "Engineering",
                "location": "San Francisco",
                "status": "Open",
            },
            headers={"Authorization": f"Bearer {recruiter_token}"}
        )
        job_id = create_response.json()["job_id"]
        
        # Update job
        update_response = client.put(
            f"/jobs/{job_id}",
            json={
                "title": "Senior Software Engineer",
                "status": "Open",
            },
            headers={"Authorization": f"Bearer {recruiter_token}"}
        )
        assert update_response.status_code == 200
        data = update_response.json()
        assert data["title"] == "Senior Software Engineer"
    
    def test_delete_job(self, client: TestClient, recruiter_token: str):
        """Test job deletion."""
        # Create job
        create_response = client.post(
            "/jobs",
            json={
                "title": "Software Engineer",
                "department": "Engineering",
                "location": "San Francisco",
                "status": "Open",
            },
            headers={"Authorization": f"Bearer {recruiter_token}"}
        )
        job_id = create_response.json()["job_id"]
        
        # Delete job
        delete_response = client.delete(
            f"/jobs/{job_id}",
            headers={"Authorization": f"Bearer {recruiter_token}"}
        )
        assert delete_response.status_code == 204
        
        # Verify deletion
        get_response = client.get(f"/jobs/{job_id}")
        assert get_response.status_code == 404


# ============ Application Tests ============

class TestApplications:
    """Test application endpoints."""
    
    @pytest.fixture
    def candidate_token(self, client: TestClient, db_session):
        """Get authenticated candidate token."""
        # Create candidate
        client.post(
            "/auth/signup/candidate",
            data={
                "full_name": "Test Candidate",
                "email": "candidate@test.com",
                "phone": "1234567890",
                "password": "SecurePass123!",
            }
        )
        
        # Login
        response = client.post(
            "/auth/login",
            json={
                "email": "candidate@test.com",
                "password": "SecurePass123!",
            }
        )
        return response.json()["access_token"]
    
    @pytest.fixture
    def job_id(self, client: TestClient, db_session):
        """Create a test job."""
        # Create recruiter and get token
        client.post(
            "/auth/signup/recruiter",
            json={
                "full_name": "Test Recruiter",
                "email": "recruiter@test.com",
                "company": "Test Company",
                "password": "SecurePass123!",
            }
        )
        
        login_response = client.post(
            "/auth/login",
            json={
                "email": "recruiter@test.com",
                "password": "SecurePass123!",
            }
        )
        recruiter_token = login_response.json()["access_token"]
        
        # Create job
        response = client.post(
            "/jobs",
            json={
                "title": "Software Engineer",
                "department": "Engineering",
                "location": "San Francisco",
                "status": "Open",
            },
            headers={"Authorization": f"Bearer {recruiter_token}"}
        )
        return response.json()["job_id"]
    
    def test_apply_for_job(self, client: TestClient, candidate_token: str, job_id: int):
        """Test applying for a job."""
        response = client.post(
            "/applications",
            json={
                "job_id": job_id,
            },
            headers={"Authorization": f"Bearer {candidate_token}"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["job_id"] == job_id
        assert "application_id" in data
    
    def test_duplicate_application(self, client: TestClient, candidate_token: str, job_id: int):
        """Test applying twice for same job."""
        # First application
        client.post(
            "/applications",
            json={"job_id": job_id},
            headers={"Authorization": f"Bearer {candidate_token}"}
        )
        
        # Second application
        response = client.post(
            "/applications",
            json={"job_id": job_id},
            headers={"Authorization": f"Bearer {candidate_token}"}
        )
        assert response.status_code == 400
    
    def test_get_applications(self, client: TestClient, candidate_token: str, job_id: int):
        """Test getting applications."""
        # Apply for job
        client.post(
            "/applications",
            json={"job_id": job_id},
            headers={"Authorization": f"Bearer {candidate_token}"}
        )
        
        # Get applications
        response = client.get(
            "/applications",
            headers={"Authorization": f"Bearer {candidate_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0


# ============ Health Check Tests ============

class TestSystem:
    """Test system endpoints."""
    
    def test_health_check(self, client: TestClient):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
    
    def test_schema_stats(self, client: TestClient):
        """Test schema statistics endpoint."""
        response = client.get("/stats/schema")
        assert response.status_code == 200
        data = response.json()
        assert "total_records" in data
        assert "candidates" in data
        assert "jobs" in data


# ============ Utility Tests ============

class TestUtilities:
    """Test utility functions."""
    
    def test_password_hashing(self):
        """Test password hashing."""
        from app.utils.security import hash_password, verify_password
        
        password = "SecurePassword123!"
        hashed = hash_password(password)
        
        assert hashed != password
        assert verify_password(password, hashed)
        assert not verify_password("WrongPassword", hashed)
    
    def test_token_creation(self):
        """Test JWT token creation."""
        from app.utils.security import create_access_token
        from jose import jwt
        from app.config import get_settings
        
        settings = get_settings()
        token = create_access_token(subject="test@test.com", role="candidate")
        
        # Decode token
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        assert payload["sub"] == "test@test.com"
        assert payload["role"] == "candidate"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
