from db_connect import get_db_connection

def test_database():
    """Test database connection and check data"""
    connection = None
    cursor = None
    
    try:
        connection = get_db_connection()
        if connection is None:
            print("❌ Database connection failed")
            return
        
        cursor = connection.cursor(dictionary=True)
        
        # Check jobs
        cursor.execute("SELECT * FROM Jobs LIMIT 5")
        jobs = cursor.fetchall()
        print(f"📋 Found {len(jobs)} jobs:")
        for job in jobs:
            print(f"  - ID: {job['job_id']}, Title: {job['title']}, Status: {job['status']}")
        
        # Check candidates
        cursor.execute("SELECT * FROM Candidates LIMIT 5")
        candidates = cursor.fetchall()
        print(f"\n👥 Found {len(candidates)} candidates:")
        for candidate in candidates:
            print(f"  - ID: {candidate['candidate_id']}, Name: {candidate['full_name']}, Email: {candidate['email']}")
        
        # Check applications
        cursor.execute("SELECT * FROM Applications LIMIT 5")
        applications = cursor.fetchall()
        print(f"\n📄 Found {len(applications)} applications:")
        for app in applications:
            print(f"  - ID: {app['application_id']}, Job: {app['job_id']}, Candidate: {app['candidate_id']}, Status: {app['status']}")
        
        # Test application submission
        if len(jobs) > 0 and len(candidates) > 0:
            print(f"\n🧪 Testing application submission...")
            cursor.execute("INSERT INTO Applications (job_id, candidate_id, status) VALUES (%s, %s, 'Applied')", 
                          (jobs[0]['job_id'], candidates[0]['candidate_id']))
            connection.commit()
            print(f"✅ Successfully submitted application for job {jobs[0]['job_id']} by candidate {candidates[0]['candidate_id']}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

if __name__ == "__main__":
    test_database()
