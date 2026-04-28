"""
Migration script to populate Users table from existing Candidates and Recruiters data.
This ensures all existing users can authenticate via the unified /auth/login endpoint.
"""
from db_connect import get_db_connection
from werkzeug.security import generate_password_hash

def migrate():
    conn = get_db_connection()
    if conn is None:
        print("Database connection failed")
        return False

    cursor = conn.cursor(dictionary=True)

    # Migrate Candidates
    cursor.execute("SELECT candidate_id, full_name, email, password_hash FROM Candidates")
    candidates = cursor.fetchall()

    migrated = 0
    for cand in candidates:
        # Check if user already exists in Users table
        cursor.execute("SELECT user_id FROM Users WHERE email = %s", (cand['email'],))
        if cursor.fetchone():
            print(f"Skipping candidate {cand['email']} - already in Users table")
            continue

        # Insert into Users table
        cursor.execute("""
            INSERT INTO Users (full_name, email, password_hash, role, candidate_id)
            VALUES (%s, %s, %s, 'candidate', %s)
        """, (cand['full_name'], cand['email'], cand['password_hash'], cand['candidate_id']))
        migrated += 1
        print(f"Migrated candidate: {cand['email']}")

    # Migrate Recruiters
    cursor.execute("SELECT recruiter_id, full_name, email, password_hash FROM Recruiters")
    recruiters = cursor.fetchall()

    for rec in recruiters:
        # Check if user already exists in Users table
        cursor.execute("SELECT user_id FROM Users WHERE email = %s", (rec['email'],))
        if cursor.fetchone():
            print(f"Skipping recruiter {rec['email']} - already in Users table")
            continue

        # Insert into Users table
        cursor.execute("""
            INSERT INTO Users (full_name, email, password_hash, role, recruiter_id)
            VALUES (%s, %s, %s, 'recruiter', %s)
        """, (rec['full_name'], rec['email'], rec['password_hash'], rec['recruiter_id']))
        migrated += 1
        print(f"Migrated recruiter: {rec['email']}")

    conn.commit()
    print(f"\nMigration complete. Total users migrated: {migrated}")

    cursor.close()
    conn.close()
    return True

if __name__ == '__main__':
    migrate()
