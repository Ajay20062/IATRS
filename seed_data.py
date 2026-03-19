from db_connect import get_db_connection

def seed_sample_data():
    """Insert sample data into existing database"""
    connection = None
    cursor = None
    
    try:
        connection = get_db_connection()
        if connection is None:
            print("❌ Database connection failed")
            return
        
        cursor = connection.cursor()
        
        # Check if candidates already exist
        cursor.execute("SELECT COUNT(*) as count FROM Candidates")
        candidates_count = cursor.fetchone()[0]
        
        if candidates_count == 0:
            print("🌱 Seeding candidates...")
            candidates_data = [
                ('Alice Williams', 'alice.williams@email.com', '+1-555-0101', 'https://resume.com/alice'),
                ('Bob Martinez', 'bob.martinez@email.com', '+1-555-0102', 'https://resume.com/bob'),
                ('Carol Davis', 'carol.davis@email.com', '+1-555-0103', 'https://resume.com/carol'),
                ('Daniel Brown', 'daniel.brown@email.com', '+1-555-0104', 'https://resume.com/daniel'),
                ('Eva Taylor', 'eva.taylor@email.com', '+1-555-0105', 'https://resume.com/eva')
            ]
            
            cursor.executemany(
                "INSERT INTO Candidates (full_name, email, phone, resume_url) VALUES (%s, %s, %s, %s)",
                candidates_data
            )
            print(f"✅ Inserted {cursor.rowcount} candidates")
        else:
            print(f"ℹ️ Candidates already exist: {candidates_count}")
        
        # Check if recruiters already exist
        cursor.execute("SELECT COUNT(*) as count FROM Recruiters")
        recruiters_count = cursor.fetchone()[0]
        
        if recruiters_count == 0:
            print("🌱 Seeding recruiters...")
            recruiters_data = [
                ('John Smith', 'john.smith@techcorp.com', 'TechCorp'),
                ('Sarah Johnson', 'sarah.johnson@innovate.com', 'Innovate Solutions'),
                ('Michael Chen', 'michael.chen@dataworks.com', 'DataWorks Inc'),
                ('Emily Rodriguez', 'emily.rodriguez@cloudify.com', 'Cloudify'),
                ('David Kim', 'david.kim@startupx.com', 'StartupX')
            ]
            
            cursor.executemany(
                "INSERT INTO Recruiters (full_name, email, company) VALUES (%s, %s, %s)",
                recruiters_data
            )
            print(f"✅ Inserted {cursor.rowcount} recruiters")
        else:
            print(f"ℹ️ Recruiters already exist: {recruiters_count}")
        
        # Check if jobs already exist
        cursor.execute("SELECT COUNT(*) as count FROM Jobs")
        jobs_count = cursor.fetchone()[0]
        
        if jobs_count == 0:
            print("🌱 Seeding jobs...")
            jobs_data = [
                (1, 'Senior Python Developer', 'Engineering', 'San Francisco, CA', 'Open'),
                (2, 'Data Scientist', 'Data Analytics', 'New York, NY', 'Open'),
                (3, 'Frontend Engineer', 'Engineering', 'Remote', 'Open'),
                (4, 'DevOps Engineer', 'Infrastructure', 'Austin, TX', 'Paused'),
                (5, 'Product Manager', 'Product', 'Seattle, WA', 'Open')
            ]
            
            cursor.executemany(
                "INSERT INTO Jobs (recruiter_id, title, department, location, status) VALUES (%s, %s, %s, %s, %s)",
                jobs_data
            )
            print(f"✅ Inserted {cursor.rowcount} jobs")
        else:
            print(f"ℹ️ Jobs already exist: {jobs_count}")
        
        connection.commit()
        print("\n🎉 Sample data seeded successfully!")
        
    except Exception as e:
        if connection:
            connection.rollback()
        print(f"❌ Error seeding data: {e}")
        
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

if __name__ == "__main__":
    seed_sample_data()
