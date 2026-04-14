from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from mysql.connector import IntegrityError
import re
from db_connect import get_db_connection

# Initialize Flask app
app = Flask(__name__)

# Enable CORS for all routes
CORS(app)

ALLOWED_ROLES = {'candidate', 'recruiter'}
ALLOWED_APPLICATION_STATUSES = {'Applied', 'Screening', 'Interviewing', 'Rejected', 'Hired'}
EMAIL_REGEX = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')

def is_valid_email(email):
    """Return True when email has a valid shape."""
    return bool(EMAIL_REGEX.match(email or ''))

def serialize_user(user):
    """Return a safe user payload for API responses."""
    return {
        'user_id': user['user_id'],
        'full_name': user['full_name'],
        'email': user['email'],
        'role': user['role'],
        'candidate_id': user['candidate_id'],
        'recruiter_id': user['recruiter_id']
    }

def safe_check_password(password_hash, password):
    """Return False for invalid hash strings instead of raising errors."""
    try:
        return check_password_hash(password_hash, password)
    except Exception:
        return False

def initialize_auth_table():
    """Create Users table if it does not exist to support login and signup."""
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        if connection is None:
            return False

        cursor = connection.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Users (
                user_id INT PRIMARY KEY AUTO_INCREMENT,
                full_name VARCHAR(100) NOT NULL,
                email VARCHAR(150) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                role ENUM('candidate', 'recruiter') NOT NULL,
                candidate_id INT UNIQUE,
                recruiter_id INT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT fk_users_candidate
                    FOREIGN KEY (candidate_id)
                    REFERENCES Candidates(candidate_id)
                    ON DELETE CASCADE,
                CONSTRAINT fk_users_recruiter
                    FOREIGN KEY (recruiter_id)
                    REFERENCES Recruiters(recruiter_id)
                    ON DELETE CASCADE
            ) ENGINE=InnoDB
            """
        )
        connection.commit()
        return True

    except Exception as e:
        print(f"Error initializing auth table: {e}")
        return False

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

initialize_auth_table()

@app.route('/auth/register', methods=['POST'])
def register_user():
    """
    Register a new candidate or recruiter account.

    Expected JSON data:
        - full_name: User name
        - email: Unique login email
        - password: Account password
        - role: candidate or recruiter
        - phone: Candidate phone (optional)
        - resume_url: Candidate resume link (optional)
        - company: Recruiter company (optional)
    """
    connection = None
    cursor = None

    try:
        data = request.get_json() or {}

        required_fields = ['full_name', 'email', 'password', 'role']
        for field in required_fields:
            if field not in data or not str(data[field]).strip():
                return jsonify({'error': f'Missing required field: {field}'}), 400

        full_name = data['full_name'].strip()
        email = data['email'].strip().lower()
        password = str(data['password'])
        role = data['role'].strip().lower()

        if role not in ALLOWED_ROLES:
            return jsonify({'error': 'Invalid role. Use candidate or recruiter'}), 400

        if not is_valid_email(email):
            return jsonify({'error': 'Invalid email format'}), 400

        if len(password) < 8:
            return jsonify({'error': 'Password must be at least 8 characters long'}), 400

        connection = get_db_connection()
        if connection is None:
            return jsonify({'error': 'Database connection failed'}), 500

        cursor = connection.cursor(dictionary=True)

        cursor.execute("SELECT user_id FROM Users WHERE email = %s", (email,))
        if cursor.fetchone():
            return jsonify({'error': 'Email already registered'}), 409

        candidate_id = None
        recruiter_id = None

        if role == 'candidate':
            phone = data.get('phone', None)
            resume_url = data.get('resume_url', None)
            cursor.execute(
                """
                INSERT INTO Candidates (full_name, email, phone, resume_url, password_hash)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    full_name,
                    email,
                    phone.strip() if isinstance(phone, str) and phone.strip() else None,
                    resume_url.strip() if isinstance(resume_url, str) and resume_url.strip() else None,
                    generate_password_hash(password)
                )
            )
            candidate_id = cursor.lastrowid
        else:
            company = data.get('company', None)
            cursor.execute(
                """
                INSERT INTO Recruiters (full_name, email, company, password_hash)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    full_name,
                    email,
                    company.strip() if isinstance(company, str) and company.strip() else None,
                    generate_password_hash(password)
                )
            )
            recruiter_id = cursor.lastrowid

        cursor.execute(
            """
            INSERT INTO Users (full_name, email, password_hash, role, candidate_id, recruiter_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                full_name,
                email,
                generate_password_hash(password),
                role,
                candidate_id,
                recruiter_id
            )
        )

        user_id = cursor.lastrowid
        connection.commit()

        return jsonify({
            'message': 'Registration successful',
            'user': {
                'user_id': user_id,
                'full_name': full_name,
                'email': email,
                'role': role,
                'candidate_id': candidate_id,
                'recruiter_id': recruiter_id
            }
        }), 201

    except IntegrityError as e:
        if connection:
            connection.rollback()
        return jsonify({'error': f'Database integrity error: {str(e)}'}), 409

    except Exception as e:
        if connection:
            connection.rollback()
        return jsonify({'error': str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

@app.route('/auth/login', methods=['POST'])
def login_user():
    """
    Authenticate a user by email and password.

    Expected JSON data:
        - email: User email
        - password: User password
    """
    connection = None
    cursor = None

    try:
        data = request.get_json() or {}
        email = str(data.get('email', '')).strip().lower()
        password = str(data.get('password', ''))

        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400

        connection = get_db_connection()
        if connection is None:
            return jsonify({'error': 'Database connection failed'}), 500

        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT user_id, full_name, email, password_hash, role, candidate_id, recruiter_id
            FROM Users
            WHERE email = %s
            """,
            (email,)
        )
        user = cursor.fetchone()

        if user is None or not check_password_hash(user['password_hash'], password):
            return jsonify({'error': 'Invalid email or password'}), 401

        return jsonify({
            'message': 'Login successful',
            'user': serialize_user(user)
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

@app.route('/register/candidate', methods=['POST'])
def register_candidate():
    """
    Register a new candidate with a securely hashed password.

    Expected JSON data:
        - full_name: Candidate full name
        - email: Candidate email
        - phone: Candidate phone number
        - password: Plain password to hash
    """
    connection = None
    cursor = None

    try:
        data = request.get_json() or {}

        required_fields = ['full_name', 'email', 'phone', 'password']
        for field in required_fields:
            if field not in data or not str(data[field]).strip():
                return jsonify({'error': f'Missing required field: {field}'}), 400

        full_name = data['full_name'].strip()
        email = data['email'].strip().lower()
        phone = data['phone'].strip()
        password = str(data['password'])

        if not is_valid_email(email):
            return jsonify({'error': 'Invalid email format'}), 400

        if len(password) < 8:
            return jsonify({'error': 'Password must be at least 8 characters long'}), 400

        connection = get_db_connection()
        if connection is None:
            return jsonify({'error': 'Database connection failed'}), 500

        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT candidate_id FROM Candidates WHERE email = %s", (email,))
        if cursor.fetchone():
            return jsonify({'error': 'Email already exists for candidate'}), 409

        sql = """
            INSERT INTO Candidates (full_name, email, phone, resume_url, password_hash)
            VALUES (%s, %s, %s, %s, %s)
        """
        values = (
            full_name,
            email,
            phone,
            data.get('resume_url', None),
            generate_password_hash(password)
        )

        cursor.execute(sql, values)
        connection.commit()

        return jsonify({
            'message': 'Candidate registered successfully',
            'candidate_id': cursor.lastrowid
        }), 201

    except Exception as e:
        if connection:
            connection.rollback()
        return jsonify({'error': str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

@app.route('/register/recruiter', methods=['POST'])
def register_recruiter():
    """
    Register a new recruiter with a securely hashed password.

    Expected JSON data:
        - full_name: Recruiter full name
        - email: Recruiter email
        - company: Recruiter company name
        - password: Plain password to hash
    """
    connection = None
    cursor = None

    try:
        data = request.get_json() or {}

        required_fields = ['full_name', 'email', 'company', 'password']
        for field in required_fields:
            if field not in data or not str(data[field]).strip():
                return jsonify({'error': f'Missing required field: {field}'}), 400

        full_name = data['full_name'].strip()
        email = data['email'].strip().lower()
        company = data['company'].strip()
        password = str(data['password'])

        if not is_valid_email(email):
            return jsonify({'error': 'Invalid email format'}), 400

        if len(password) < 8:
            return jsonify({'error': 'Password must be at least 8 characters long'}), 400

        connection = get_db_connection()
        if connection is None:
            return jsonify({'error': 'Database connection failed'}), 500

        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT recruiter_id FROM Recruiters WHERE email = %s", (email,))
        if cursor.fetchone():
            return jsonify({'error': 'Email already exists for recruiter'}), 409

        sql = """
            INSERT INTO Recruiters (full_name, email, company, password_hash)
            VALUES (%s, %s, %s, %s)
        """
        values = (
            full_name,
            email,
            company,
            generate_password_hash(password)
        )

        cursor.execute(sql, values)
        connection.commit()

        return jsonify({
            'message': 'Recruiter registered successfully',
            'recruiter_id': cursor.lastrowid
        }), 201

    except Exception as e:
        if connection:
            connection.rollback()
        return jsonify({'error': str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

@app.route('/login', methods=['POST'])
def login_with_role():
    """
    Login endpoint that authenticates against Candidates or Recruiters by role.

    Expected JSON data:
        - email: User email
        - password: User password
        - role: candidate or recruiter
    """
    connection = None
    cursor = None

    try:
        data = request.get_json() or {}
        email = str(data.get('email', '')).strip().lower()
        password = str(data.get('password', ''))
        role = str(data.get('role', '')).strip().lower()

        if not email or not password or not role:
            return jsonify({'error': 'Email, password, and role are required'}), 400

        if role not in ALLOWED_ROLES:
            return jsonify({'error': 'Role must be candidate or recruiter'}), 400

        connection = get_db_connection()
        if connection is None:
            return jsonify({'error': 'Database connection failed'}), 500

        cursor = connection.cursor(dictionary=True)

        if role == 'candidate':
            cursor.execute(
                """
                SELECT candidate_id AS user_id, full_name, email, password_hash
                FROM Candidates
                WHERE email = %s
                """,
                (email,)
            )
        else:
            cursor.execute(
                """
                SELECT recruiter_id AS user_id, full_name, email, password_hash
                FROM Recruiters
                WHERE email = %s
                """,
                (email,)
            )

        user = cursor.fetchone()

        if user is None or not safe_check_password(user['password_hash'], password):
            return jsonify({'error': 'Invalid credentials'}), 401

        response_user = {
            'id': user['user_id'],
            'full_name': user['full_name'],
            'email': user['email'],
            'role': role
        }

        if role == 'candidate':
            response_user['candidate_id'] = user['user_id']
        else:
            response_user['recruiter_id'] = user['user_id']

        return jsonify({
            'message': 'Login successful',
            'user': response_user
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

@app.route('/')
def index():
    """
    Test route to verify the API is running.
    
    Returns:
        JSON response with success message
    """
    return jsonify({'message': 'ATS API is running successfully!'})

@app.route('/jobs', methods=['GET'])
def get_jobs():
    """
    Fetch all jobs from the Jobs table.
    
    Returns:
        JSON list of all jobs
    """
    connection = None
    cursor = None
    
    try:
        connection = get_db_connection()
        if connection is None:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Jobs")
        jobs = cursor.fetchall()
        
        return jsonify(jobs), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
        
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

@app.route('/jobs/<int:id>', methods=['GET'])
def get_job(id):
    """
    Fetch a single job by its ID.
    
    Args:
        id: Job ID
        
    Returns:
        JSON object of the job or error message
    """
    connection = None
    cursor = None
    
    try:
        connection = get_db_connection()
        if connection is None:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Jobs WHERE job_id = %s", (id,))
        job = cursor.fetchone()
        
        if job is None:
            return jsonify({'error': 'Job not found'}), 404
        
        return jsonify(job), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
        
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

@app.route('/jobs', methods=['POST'])
def create_job():
    """
    Create a new job posting.
    
    Expected JSON data:
        - title: Job title
        - department: Department name
        - location: Job location
        - recruiter_id: ID of the recruiter posting the job
        
    Returns:
        JSON success message or error
    """
    connection = None
    cursor = None
    
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['title', 'department', 'location', 'recruiter_id']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        connection = get_db_connection()
        if connection is None:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = connection.cursor()
        
        # Insert new job
        sql = """
            INSERT INTO Jobs (recruiter_id, title, department, location)
            VALUES (%s, %s, %s, %s)
        """
        values = (
            data['recruiter_id'],
            data['title'],
            data['department'],
            data['location']
        )
        
        cursor.execute(sql, values)
        connection.commit()
        
        return jsonify({
            'message': 'Job created successfully',
            'job_id': cursor.lastrowid
        }), 201
        
    except Exception as e:
        if connection:
            connection.rollback()
        return jsonify({'error': str(e)}), 500
        
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

@app.route('/apply', methods=['POST'])
def apply_for_job():
    """
    Allow a candidate to apply for a job.
    
    Expected JSON data:
        - candidate_id: ID of the candidate applying
        - job_id: ID of the job being applied to
        
    Returns:
        JSON success message or error
    """
    connection = None
    cursor = None
    
    try:
        data = request.get_json()
        
        # Validate required fields
        if 'candidate_id' not in data or 'job_id' not in data:
            return jsonify({'error': 'Missing required fields: candidate_id and job_id'}), 400
        
        connection = get_db_connection()
        if connection is None:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = connection.cursor()
        
        # Insert application
        sql = """
            INSERT INTO Applications (job_id, candidate_id, status)
            VALUES (%s, %s, 'Applied')
        """
        values = (data['job_id'], data['candidate_id'])
        
        cursor.execute(sql, values)
        connection.commit()
        
        return jsonify({
            'message': 'Application submitted successfully',
            'application_id': cursor.lastrowid
        }), 201
        
    except Exception as e:
        if connection:
            connection.rollback()
        return jsonify({'error': str(e)}), 500
        
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

@app.route('/applications/<int:app_id>/status', methods=['PUT'])
def update_application_status(app_id):
    """
    Update the status of an application.

    Expected JSON data:
        - status: New application status

    Args:
        app_id: Application ID

    Returns:
        JSON success message or error
    """
    connection = None
    cursor = None

    try:
        data = request.get_json()

        if not data or 'status' not in data:
            return jsonify({'error': 'Missing required field: status'}), 400

        new_status = str(data['status']).strip()
        if new_status not in ALLOWED_APPLICATION_STATUSES:
            return jsonify({'error': 'Invalid status value'}), 400

        connection = get_db_connection()
        if connection is None:
            return jsonify({'error': 'Database connection failed'}), 500

        cursor = connection.cursor()

        sql = """
            UPDATE Applications
            SET status = %s
            WHERE application_id = %s
        """
        values = (new_status, app_id)

        cursor.execute(sql, values)
        connection.commit()

        if cursor.rowcount == 0:
            return jsonify({'error': 'Application not found'}), 404

        return jsonify({'message': 'Status updated successfully'}), 200

    except Exception as e:
        if connection:
            connection.rollback()
        return jsonify({'error': str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

@app.route('/applications/candidate/<int:candidate_id>', methods=['GET'])
def get_candidate_applications(candidate_id):
    """
    Fetch all applications for a specific candidate with job details.

    Args:
        candidate_id: Candidate ID

    Returns:
        JSON list of candidate applications
    """
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        if connection is None:
            return jsonify({'error': 'Database connection failed'}), 500

        cursor = connection.cursor(dictionary=True)

        sql = """
            SELECT
                a.application_id,
                a.candidate_id,
                a.status,
                a.created_at,
                j.job_id,
                j.title AS job_title,
                j.department,
                j.location
            FROM Applications a
            INNER JOIN Jobs j ON a.job_id = j.job_id
            WHERE a.candidate_id = %s
            ORDER BY a.created_at DESC
        """

        cursor.execute(sql, (candidate_id,))
        applications = cursor.fetchall()

        return jsonify(applications), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

@app.route('/applications', methods=['GET'])
def get_applications():
    """
    Fetch all applications with candidate and job details using SQL JOIN.
    
    Returns:
        JSON list of applications with joined data from Candidates and Jobs tables
    """
    connection = None
    cursor = None
    
    try:
        connection = get_db_connection()
        if connection is None:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = connection.cursor(dictionary=True)
        
        # SQL JOIN query to fetch application details
        sql = """
            SELECT 
                a.application_id,
                c.full_name AS candidate_name,
                c.email AS candidate_email,
                j.title AS job_title,
                j.department,
                j.location,
                a.status,
                a.created_at
            FROM Applications a
            INNER JOIN Candidates c ON a.candidate_id = c.candidate_id
            INNER JOIN Jobs j ON a.job_id = j.job_id
            ORDER BY a.created_at DESC
        """
        
        cursor.execute(sql)
        applications = cursor.fetchall()
        
        return jsonify(applications), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
        
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

if __name__ == '__main__':
    initialize_auth_table()
    app.run(debug=True, port=5001)
