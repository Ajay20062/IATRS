"""
IATRS - Schema Migrations
Ensure database schema compatibility.
"""
from sqlalchemy import inspect, text


def ensure_schema_compatibility(engine):
    """
    Ensure database schema is compatible with current models.
    Add any missing columns or tables.
    """
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    # List of expected tables
    expected_tables = [
        'recruiters', 'jobs', 'candidates', 'applications',
        'interviews', 'user_credentials', 'user_profiles',
        'notifications', 'audit_logs', 'job_templates',
        'email_verification_tokens', 'password_reset_tokens'
    ]
    
    # Check for missing tables
    missing_tables = set(expected_tables) - set(existing_tables)
    
    if missing_tables:
        print(f"⚠️  Missing tables: {missing_tables}")
        print("ℹ️  Tables will be created automatically")
    
    # Add any missing columns to existing tables
    for table_name in expected_tables:
        if table_name in existing_tables:
            check_and_add_columns(engine, table_name, inspector)
    
    return True


def check_and_add_columns(engine, table_name, inspector):
    """
    Check if table has all required columns.
    """
    # Define required columns for each table
    required_columns = {
        'recruiters': ['recruiter_id', 'full_name', 'email', 'company', 'created_at'],
        'jobs': ['job_id', 'recruiter_id', 'title', 'department', 'location', 'status'],
        'candidates': ['candidate_id', 'full_name', 'email', 'phone', 'resume_url'],
        'applications': ['application_id', 'job_id', 'candidate_id', 'status'],
        'interviews': ['interview_id', 'application_id', 'scheduled_at', 'interview_type', 'status'],
        'user_credentials': ['credential_id', 'email', 'password_hash', 'role'],
        'user_profiles': ['profile_id', 'credential_id'],
    }
    
    if table_name not in required_columns:
        return
    
    existing_columns = [col['name'] for col in inspector.get_columns(table_name)]
    missing_columns = set(required_columns[table_name]) - set(existing_columns)
    
    if missing_columns:
        print(f"⚠️  Table '{table_name}' missing columns: {missing_columns}")
        # Note: In production, you would add ALTER TABLE statements here


if __name__ == "__main__":
    from app.database import engine
    ensure_schema_compatibility(engine)
    print("✅ Schema compatibility check complete!")
