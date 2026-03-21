"""
IATRS - Comprehensive Seed Data Script
Populates the database with sample data for testing.
"""
import os
from datetime import datetime, timedelta

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import (
    Recruiter, Job, Candidate, Application, Interview,
    UserCredential, UserProfile
)
from app.utils.security import hash_password

# Load environment variables
load_dotenv()

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./iatrs.db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def seed_database():
    """Seed the database with sample data."""
    print("🌱 Starting database seeding...")
    
    db = SessionLocal()
    
    try:
        # Check if data already exists
        if db.query(Recruiter).count() > 0:
            print("⚠️  Database already has data. Skipping seed.")
            return
        
        # ============ Create Recruiters ============
        print("📝 Creating recruiters...")
        
        recruiters = [
            Recruiter(
                full_name="Sarah Johnson",
                email="sarah@techcorp.com",
                company="TechCorp Inc."
            ),
            Recruiter(
                full_name="Michael Chen",
                email="michael@innovate.io",
                company="Innovate.io"
            ),
            Recruiter(
                full_name="Emily Davis",
                email="emily@startup.co",
                company="Startup Co"
            ),
        ]
        
        for recruiter in recruiters:
            db.add(recruiter)
            db.flush()
            
            # Create credentials for each recruiter
            credential = UserCredential(
                email=recruiter.email,
                password_hash=hash_password("password123"),
                role="recruiter",
                recruiter_id=recruiter.recruiter_id,
                is_verified=True,
                is_active=True,
            )
            db.add(credential)
            db.flush()
            
            # Create profile
            profile = UserProfile(
                credential_id=credential.credential_id,
                full_name=recruiter.full_name,
                company_name=recruiter.company,
                designation="Senior Recruiter",
            )
            db.add(profile)
        
        db.commit()
        print(f"✅ Created {len(recruiters)} recruiters")
        
        # ============ Create Candidates ============
        print("👨‍🎓 Creating candidates...")
        
        candidates = [
            Candidate(
                full_name="John Doe",
                email="john.doe@email.com",
                phone="+1-555-0101",
                current_title="Software Engineer",
                current_company="Previous Corp",
                total_experience_years=3.5,
                expected_salary=90000,
            ),
            Candidate(
                full_name="Jane Smith",
                email="jane.smith@email.com",
                phone="+1-555-0102",
                current_title="Senior Developer",
                current_company="Tech Solutions",
                total_experience_years=5.0,
                expected_salary=120000,
            ),
            Candidate(
                full_name="Robert Wilson",
                email="robert.wilson@email.com",
                phone="+1-555-0103",
                current_title="Full Stack Developer",
                current_company="Web Dev Inc",
                total_experience_years=4.0,
                expected_salary=100000,
            ),
            Candidate(
                full_name="Alice Brown",
                email="alice.brown@email.com",
                phone="+1-555-0104",
                current_title="Data Scientist",
                current_company="Analytics Co",
                total_experience_years=2.5,
                expected_salary=95000,
            ),
            Candidate(
                full_name="David Lee",
                email="david.lee@email.com",
                phone="+1-555-0105",
                current_title="DevOps Engineer",
                current_company="Cloud Systems",
                total_experience_years=6.0,
                expected_salary=130000,
            ),
        ]
        
        for candidate in candidates:
            db.add(candidate)
            db.flush()
            
            # Create credentials
            credential = UserCredential(
                email=candidate.email,
                password_hash=hash_password("password123"),
                role="candidate",
                candidate_id=candidate.candidate_id,
                is_verified=True,
                is_active=True,
            )
            db.add(credential)
            db.flush()
            
            # Create profile
            profile = UserProfile(
                credential_id=credential.credential_id,
                full_name=candidate.full_name,
                phone_number=candidate.phone,
                skills=", ".join([
                    "Python", "JavaScript", "SQL", 
                    "Git", "Agile"
                ]),
                experience=f"{candidate.current_title} at {candidate.current_company}",
            )
            db.add(profile)
        
        db.commit()
        print(f"✅ Created {len(candidates)} candidates")
        
        # ============ Create Jobs ============
        print("💼 Creating jobs...")
        
        recruiter_list = db.query(Recruiter).all()
        
        jobs = [
            Job(
                recruiter_id=recruiter_list[0].recruiter_id,
                title="Senior Software Engineer",
                description="We are looking for an experienced software engineer to join our team.",
                requirements="5+ years experience, Python, JavaScript, SQL",
                department="Engineering",
                location="San Francisco, CA",
                work_mode="Hybrid",
                min_salary=120000,
                max_salary=160000,
                required_skills="Python,JavaScript,SQL,React",
                min_experience_years=5,
                education_level="Bachelors",
                status="Open",
                is_featured=True,
            ),
            Job(
                recruiter_id=recruiter_list[0].recruiter_id,
                title="Frontend Developer",
                description="Looking for a talented frontend developer with React expertise.",
                requirements="3+ years experience, React, TypeScript, CSS",
                department="Engineering",
                location="New York, NY",
                work_mode="Remote",
                min_salary=90000,
                max_salary=130000,
                required_skills="React,TypeScript,CSS,HTML",
                min_experience_years=3,
                status="Open",
            ),
            Job(
                recruiter_id=recruiter_list[1].recruiter_id,
                title="Data Scientist",
                description="Join our data science team to build ML models.",
                requirements="Masters in CS/Stats, Python, ML frameworks",
                department="Data Science",
                location="Boston, MA",
                work_mode="Hybrid",
                min_salary=110000,
                max_salary=150000,
                required_skills="Python,Machine Learning,TensorFlow,SQL",
                min_experience_years=2,
                education_level="Masters",
                status="Open",
            ),
            Job(
                recruiter_id=recruiter_list[1].recruiter_id,
                title="DevOps Engineer",
                description="Manage our cloud infrastructure and CI/CD pipelines.",
                requirements="AWS, Kubernetes, Docker, Terraform",
                department="Infrastructure",
                location="Seattle, WA",
                work_mode="Onsite",
                min_salary=130000,
                max_salary=170000,
                required_skills="AWS,Kubernetes,Docker,Terraform",
                min_experience_years=4,
                status="Open",
            ),
            Job(
                recruiter_id=recruiter_list[2].recruiter_id,
                title="Full Stack Developer",
                description="Build end-to-end web applications.",
                requirements="Node.js, React, MongoDB, REST APIs",
                department="Product",
                location="Austin, TX",
                work_mode="Hybrid",
                min_salary=100000,
                max_salary=140000,
                required_skills="Node.js,React,MongoDB,JavaScript",
                min_experience_years=3,
                status="Open",
            ),
        ]
        
        for job in jobs:
            db.add(job)
        
        db.commit()
        print(f"✅ Created {len(jobs)} jobs")
        
        # ============ Create Applications ============
        print("📬 Creating applications...")
        
        candidate_list = db.query(Candidate).all()
        job_list = db.query(Job).all()
        
        applications = [
            Application(
                job_id=job_list[0].job_id,
                candidate_id=candidate_list[0].candidate_id,
                status="Screening",
                match_score=85.5,
                cover_letter="I am excited to apply for this position...",
            ),
            Application(
                job_id=job_list[0].job_id,
                candidate_id=candidate_list[1].candidate_id,
                status="Interviewing",
                match_score=92.0,
                cover_letter="With my extensive experience...",
            ),
            Application(
                job_id=job_list[1].job_id,
                candidate_id=candidate_list[2].candidate_id,
                status="Applied",
                match_score=78.0,
            ),
            Application(
                job_id=job_list[2].job_id,
                candidate_id=candidate_list[3].candidate_id,
                status="Interviewing",
                match_score=88.5,
                cover_letter="My background in data science...",
            ),
            Application(
                job_id=job_list[3].job_id,
                candidate_id=candidate_list[4].candidate_id,
                status="Applied",
                match_score=95.0,
            ),
            Application(
                job_id=job_list[4].job_id,
                candidate_id=candidate_list[0].candidate_id,
                status="Applied",
                match_score=72.0,
            ),
        ]
        
        for application in applications:
            db.add(application)
        
        db.commit()
        print(f"✅ Created {len(applications)} applications")
        
        # ============ Create Interviews ============
        print("🎤 Creating interviews...")
        
        application_list = db.query(Application).all()
        
        interviews = [
            Interview(
                application_id=application_list[1].application_id,
                scheduled_at=datetime.now() + timedelta(days=2),
                interview_type="Video",
                status="Scheduled",
                interviewer_name="Sarah Johnson",
                interviewer_email="sarah@techcorp.com",
                interview_link="https://zoom.us/j/123456789",
            ),
            Interview(
                application_id=application_list[3].application_id,
                scheduled_at=datetime.now() + timedelta(days=3),
                interview_type="Video",
                status="Scheduled",
                interviewer_name="Michael Chen",
                interviewer_email="michael@innovate.io",
                interview_link="https://zoom.us/j/987654321",
            ),
            Interview(
                application_id=application_list[0].application_id,
                scheduled_at=datetime.now() - timedelta(days=5),
                interview_type="Phone",
                status="Completed",
                interviewer_name="Sarah Johnson",
                feedback="Good technical skills, strong communication.",
                interview_score=85,
                recommendation="Hire",
                technical_score=88,
                communication_score=90,
                cultural_fit_score=82,
            ),
        ]
        
        for interview in interviews:
            db.add(interview)
        
        db.commit()
        print(f"✅ Created {len(interviews)} interviews")
        
        # ============ Summary ============
        print("\n" + "=" * 50)
        print("🎉 Database seeding completed successfully!")
        print("=" * 50)
        print(f"\n📊 Summary:")
        print(f"   Recruiters:  {db.query(Recruiter).count()}")
        print(f"   Candidates:  {db.query(Candidate).count()}")
        print(f"   Jobs:        {db.query(Job).count()}")
        print(f"   Applications: {db.query(Application).count()}")
        print(f"   Interviews:  {db.query(Interview).count()}")
        print(f"\n🔐 Test Credentials:")
        print(f"   All passwords are: password123")
        print(f"\n   Recruiters:")
        for r in recruiters:
            print(f"     - {r.email}")
        print(f"\n   Candidates:")
        for c in candidates:
            print(f"     - {c.email}")
        print("\n" + "=" * 50)
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
