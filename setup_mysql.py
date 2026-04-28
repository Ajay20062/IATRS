from db_connect import get_db_connection
from werkzeug.security import generate_password_hash
import os

def execute_schema_file(cursor, schema_file_path):
    """
    Read and execute SQL schema file.
    
    Args:
        cursor: MySQL cursor object
        schema_file_path: Path to the schema.sql file
    """
    try:
        with open(schema_file_path, 'r') as file:
            schema_sql = file.read()
        
        # Split SQL commands by semicolon and execute each
        sql_commands = schema_sql.split(';')
        
        for command in sql_commands:
            command = command.strip()
            if command:  # Skip empty commands
                cursor.execute(command)
                print(f"Executed: {command[:50]}...")
        
        print("Schema created successfully!")
        
    except Exception as e:
        print(f"Error executing schema: {e}")
        raise

def seed_data(cursor):
    """
    Insert dummy data into the database.
    
    Args:
        cursor: MySQL cursor object
    """
    try:
        default_password_hash = generate_password_hash('Password@123')

        # Insert 5 dummy Recruiters first (needed for foreign key in Jobs)
        recruiters_data = [
            ('John Smith', 'john.smith@techcorp.com', 'TechCorp', default_password_hash),
            ('Sarah Johnson', 'sarah.johnson@innovate.com', 'Innovate Solutions', default_password_hash),
            ('Michael Chen', 'michael.chen@dataworks.com', 'DataWorks Inc', default_password_hash),
            ('Emily Rodriguez', 'emily.rodriguez@cloudify.com', 'Cloudify', default_password_hash),
            ('David Kim', 'david.kim@startupx.com', 'StartupX', default_password_hash)
        ]
        
        cursor.executemany(
            "INSERT INTO Recruiters (full_name, email, company, password_hash) VALUES (%s, %s, %s, %s)",
            recruiters_data
        )
        print(f"Inserted {cursor.rowcount} recruiters")
        
        # Insert 5 dummy Jobs
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
        print(f"Inserted {cursor.rowcount} jobs")
        
        # Insert 5 dummy Candidates
        candidates_data = [
            ('Alice Williams', 'alice.williams@email.com', '+1-555-0101', 'https://resume.com/alice', default_password_hash),
            ('Bob Martinez', 'bob.martinez@email.com', '+1-555-0102', 'https://resume.com/bob', default_password_hash),
            ('Carol Davis', 'carol.davis@email.com', '+1-555-0103', 'https://resume.com/carol', default_password_hash),
            ('Daniel Brown', 'daniel.brown@email.com', '+1-555-0104', 'https://resume.com/daniel', default_password_hash),
            ('Eva Taylor', 'eva.taylor@email.com', '+1-555-0105', 'https://resume.com/eva', default_password_hash)
        ]
        
        cursor.executemany(
            "INSERT INTO Candidates (full_name, email, phone, resume_url, password_hash) VALUES (%s, %s, %s, %s, %s)",
            candidates_data
        )
        print(f"Inserted {cursor.rowcount} candidates")

        # Insert login accounts for all seeded users
        users_data = []

        for recruiter_id, recruiter in enumerate(recruiters_data, start=1):
            users_data.append(
                (
                    recruiter[0],
                    recruiter[1],
                    default_password_hash,
                    'recruiter',
                    None,
                    recruiter_id
                )
            )

        for candidate_id, candidate in enumerate(candidates_data, start=1):
            users_data.append(
                (
                    candidate[0],
                    candidate[1],
                    default_password_hash,
                    'candidate',
                    candidate_id,
                    None
                )
            )

        cursor.executemany(
            """
            INSERT INTO Users (full_name, email, password_hash, role, candidate_id, recruiter_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            users_data
        )
        print(f"Inserted {cursor.rowcount} user accounts")
        
    except Exception as e:
        print(f"Error seeding data: {e}")
        raise

def main():
    """
    Main function to set up the MySQL database with schema and seed data.
    """
    connection = None
    cursor = None
    
    try:
        # Get database connection
        connection = get_db_connection()
        
        if connection is None:
            print("Failed to connect to database. Exiting.")
            return
        
        cursor = connection.cursor()
        
        # Execute schema file
        schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
        execute_schema_file(cursor, schema_path)
        
        # Seed dummy data
        seed_data(cursor)
        
        # Commit all changes
        connection.commit()
        
        print("\n" + "="*50)
        print("MySQL Database ats_db initialized successfully!")
        print("Default password for all seeded login accounts: Password@123")
        print("="*50)
        
    except Exception as e:
        if connection:
            connection.rollback()
        print(f"\nSetup failed: {e}")
        
    finally:
        # Close cursor and connection
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()
            print("Database connection closed.")

if __name__ == "__main__":
    main()
