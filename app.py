from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from mysql.connector import IntegrityError
import re
import os
import logging
from datetime import datetime
from db_connect import get_db_connection

# Initialize Flask app
app = Flask(__name__)

# Flask configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['DEBUG'] = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Enable CORS for all routes
CORS(app)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

ALLOWED_ROLES = {'candidate', 'recruiter'}
ALLOWED_APPLICATION_STATUSES = {'Applied', 'Screening', 'Interviewing', 'Rejected', 'Hired'}
ALLOWED_INTERVIEW_TYPES = {'Phone', 'Video', 'Onsite'}
ALLOWED_INTERVIEW_STATUSES = {'Scheduled', 'Completed', 'No-Show', 'Cancelled'}
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

def format_integrity_error(error):
    """Return user-friendly messages for common database integrity violations."""
    message = str(error).lower()

    if ('duplicate entry' in message or 'unique' in message) and (
        'applications' in message or 'job_id' in message and 'candidate_id' in message
    ):
        return 'You have already applied for this job'

    if 'duplicate entry' in message and 'email' in message:
        return 'Email already exists'

    if 'foreign key' in message:
        return 'Referenced record was not found. Please refresh and try again'

    return 'Database integrity constraint failed'

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

def initialize_interview_artifacts():
    """Create interview view and trigger required for end-to-end workflow."""
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        if connection is None:
            return False

        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            CREATE OR REPLACE VIEW Scheduled_Interviews AS
            SELECT interview_id, application_id, scheduled_at, interview_type, status
            FROM Interviews
            WHERE status = 'Scheduled'
            """
        )

        cursor.execute(
            """
            SELECT COUNT(*) AS count
            FROM information_schema.triggers
            WHERE trigger_schema = DATABASE()
              AND trigger_name = 'trg_update_application_status'
            """
        )
        trigger_exists = cursor.fetchone()['count'] > 0

        if not trigger_exists:
            cursor.execute(
                """
                CREATE TRIGGER trg_update_application_status
                AFTER UPDATE ON Interviews
                FOR EACH ROW
                UPDATE Applications
                SET status = 'Interviewing'
                WHERE NEW.status = 'Completed'
                  AND application_id = NEW.application_id
                """
            )

        connection.commit()
        return True

    except Exception as e:
        print(f"Error initializing interview artifacts: {e}")
        return False

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

initialize_auth_table()
initialize_interview_artifacts()

@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint to verify service and database connectivity.
    """
    try:
        connection = get_db_connection()
        if connection:
            connection.close()
            logger.info("Health check passed - database connected")
            return jsonify({
                'status': 'healthy',
                'database': 'connected',
                'timestamp': datetime.now().isoformat()
            }), 200
        else:
            logger.warning("Health check failed - database disconnected")
            return jsonify({
                'status': 'unhealthy',
                'database': 'disconnected',
                'timestamp': datetime.now().isoformat()
            }), 503
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

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

    except IntegrityError as e:
        if connection:
            connection.rollback()
        return jsonify({'error': format_integrity_error(e)}), 409

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

    except IntegrityError as e:
        if connection:
            connection.rollback()
        return jsonify({'error': format_integrity_error(e)}), 409

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
            'user_id': user['user_id'],
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
    return jsonify({
        'message': 'ATS API is running successfully!',
        'database': os.getenv('DB_NAME')
    })

@app.route('/meta/db-info', methods=['GET'])
def get_database_info():
    """Return current database metadata to help verify environment wiring."""
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        if connection is None:
            return jsonify({'error': 'Database connection failed'}), 500

        cursor = connection.cursor(dictionary=True)
        cursor.execute('SELECT DATABASE() AS current_database')
        db_row = cursor.fetchone()

        cursor.execute('SELECT COUNT(*) AS count FROM Recruiters')
        recruiters = cursor.fetchone()['count']
        cursor.execute('SELECT COUNT(*) AS count FROM Candidates')
        candidates = cursor.fetchone()['count']
        cursor.execute('SELECT COUNT(*) AS count FROM Jobs')
        jobs = cursor.fetchone()['count']
        cursor.execute('SELECT COUNT(*) AS count FROM Applications')
        applications = cursor.fetchone()['count']

        return jsonify({
            'database': db_row['current_database'],
            'env_db_name': os.getenv('DB_NAME'),
            'counts': {
                'recruiters': recruiters,
                'candidates': candidates,
                'jobs': jobs,
                'applications': applications
            }
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

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

@app.route('/jobs/recruiter/<int:recruiter_id>', methods=['GET'])
def get_jobs_by_recruiter(recruiter_id):
    """
    Fetch jobs posted by a specific recruiter.

    Args:
        recruiter_id: Recruiter ID

    Returns:
        JSON list of jobs posted by the recruiter
    """
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        if connection is None:
            return jsonify({'error': 'Database connection failed'}), 500

        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT job_id, recruiter_id, title, department, location, status, created_at
            FROM Jobs
            WHERE recruiter_id = %s
            ORDER BY created_at DESC
            """,
            (recruiter_id,)
        )

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
        data = request.get_json() or {}
        
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
        
    except IntegrityError as e:
        if connection:
            connection.rollback()
        return jsonify({'error': format_integrity_error(e)}), 409

    except Exception as e:
        if connection:
            connection.rollback()
        return jsonify({'error': str(e)}), 500
        
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

# ===== ADVANCED FEATURES =====

@app.route('/jobs/search', methods=['GET'])
def advanced_job_search():
    """
    Advanced job search with multiple filters.

    Query parameters:
        - q: General search query (title, department, location)
        - location: Specific location filter
        - department: Department filter
        - recruiter_id: Filter by recruiter
        - status: Job status (Open, Closed, Paused)
        - min_experience: Minimum experience level (optional)
        - max_experience: Maximum experience level (optional)
        - sort_by: Sort field (created_at, title, location)
        - sort_order: Sort order (asc, desc)
        - page: Page number (default: 1)
        - per_page: Results per page (default: 10)
    """
    connection = None
    cursor = None

    try:
        # Get query parameters
        search_query = request.args.get('q', '').strip()
        location = request.args.get('location', '').strip()
        department = request.args.get('department', '').strip()
        recruiter_id = request.args.get('recruiter_id', '').strip()
        status = request.args.get('status', 'Open')  # Default to open jobs
        min_exp = request.args.get('min_experience', '').strip()
        max_exp = request.args.get('max_experience', '').strip()
        sort_by = request.args.get('sort_by', 'created_at')
        sort_order = request.args.get('sort_order', 'desc')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))

        # Validate sort parameters
        allowed_sort_fields = ['created_at', 'title', 'location', 'department']
        if sort_by not in allowed_sort_fields:
            sort_by = 'created_at'
        if sort_order not in ['asc', 'desc']:
            sort_order = 'desc'

        connection = get_db_connection()
        if connection is None:
            return jsonify({'error': 'Database connection failed'}), 500

        cursor = connection.cursor(dictionary=True)

        # Build dynamic query
        base_query = """
            SELECT j.job_id, j.title, j.department, j.location, j.status, j.created_at,
                   r.full_name as recruiter_name, r.company,
                   COUNT(a.application_id) as application_count
            FROM Jobs j
            JOIN Recruiters r ON j.recruiter_id = r.recruiter_id
            LEFT JOIN Applications a ON j.job_id = a.job_id
        """

        where_conditions = []
        params = []

        # Add filters
        if search_query:
            where_conditions.append("(j.title LIKE %s OR j.department LIKE %s OR j.location LIKE %s)")
            search_param = f"%{search_query}%"
            params.extend([search_param, search_param, search_param])

        if location:
            where_conditions.append("j.location LIKE %s")
            params.append(f"%{location}%")

        if department:
            where_conditions.append("j.department LIKE %s")
            params.append(f"%{department}%")

        if recruiter_id:
            where_conditions.append("j.recruiter_id = %s")
            params.append(recruiter_id)

        if status:
            where_conditions.append("j.status = %s")
            params.append(status)

        # Build WHERE clause
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"

        # Complete query with GROUP BY, ORDER BY, LIMIT
        query = f"""
            {base_query}
            WHERE {where_clause}
            GROUP BY j.job_id, j.title, j.department, j.location, j.status, j.created_at, r.full_name, r.company
            ORDER BY j.{sort_by} {sort_order}
            LIMIT %s OFFSET %s
        """

        # Calculate offset
        offset = (page - 1) * per_page
        params.extend([per_page, offset])

        cursor.execute(query, params)
        jobs = cursor.fetchall()

        # Get total count for pagination
        count_query = f"""
            SELECT COUNT(DISTINCT j.job_id) as total
            FROM Jobs j
            JOIN Recruiters r ON j.recruiter_id = r.recruiter_id
            LEFT JOIN Applications a ON j.job_id = a.job_id
            WHERE {where_clause}
        """
        cursor.execute(count_query, params[:-2])  # Remove LIMIT and OFFSET params
        total_result = cursor.fetchone()
        total_jobs = total_result['total'] if total_result else 0

        return jsonify({
            'jobs': jobs,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total_jobs,
                'total_pages': (total_jobs + per_page - 1) // per_page
            },
            'filters_applied': {
                'query': search_query,
                'location': location,
                'department': department,
                'recruiter_id': recruiter_id,
                'status': status
            }
        }), 200

    except Exception as e:
        logger.error(f"Advanced job search error: {str(e)}")
        return jsonify({'error': str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

@app.route('/jobs/recommend/<int:candidate_id>', methods=['GET'])
def get_job_recommendations(candidate_id):
    """
    Get personalized job recommendations for a candidate.

    Uses candidate's application history and profile to suggest relevant jobs.
    """
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        if connection is None:
            return jsonify({'error': 'Database connection failed'}), 500

        cursor = connection.cursor(dictionary=True)

        # Get candidate's application history to understand preferences
        cursor.execute("""
            SELECT j.department, j.location, COUNT(*) as application_count
            FROM Applications a
            JOIN Jobs j ON a.job_id = j.job_id
            WHERE a.candidate_id = %s
            GROUP BY j.department, j.location
            ORDER BY application_count DESC
            LIMIT 5
        """, (candidate_id,))

        preferences = cursor.fetchall()

        # Build recommendation query based on preferences
        if preferences:
            # Create dynamic conditions based on candidate's history
            dept_conditions = [f"j.department = '{pref['department']}'" for pref in preferences]
            loc_conditions = [f"j.location LIKE '%{pref['location']}%'" for pref in preferences]

            dept_clause = " OR ".join(dept_conditions)
            loc_clause = " OR ".join(loc_conditions)

            query = f"""
                SELECT j.job_id, j.title, j.department, j.location, j.created_at,
                       r.full_name as recruiter_name, r.company,
                       COUNT(a.application_id) as application_count,
                       CASE
                           WHEN j.department IN ({', '.join([f"'{pref['department']}'" for pref in preferences])}) THEN 3
                           WHEN j.location LIKE CONCAT('%', c.location_pref, '%') THEN 2
                           ELSE 1
                       END as relevance_score
                FROM Jobs j
                JOIN Recruiters r ON j.recruiter_id = r.recruiter_id
                LEFT JOIN Applications a ON j.job_id = a.job_id
                CROSS JOIN (SELECT '{preferences[0]['location']}' as location_pref) c
                WHERE j.status = 'Open'
                AND j.job_id NOT IN (
                    SELECT job_id FROM Applications WHERE candidate_id = %s
                )
                GROUP BY j.job_id, j.title, j.department, j.location, j.created_at, r.full_name, r.company
                ORDER BY relevance_score DESC, j.created_at DESC
                LIMIT 10
            """
        else:
            # Default recommendations for new candidates
            query = """
                SELECT j.job_id, j.title, j.department, j.location, j.created_at,
                       r.full_name as recruiter_name, r.company,
                       COUNT(a.application_id) as application_count,
                       1 as relevance_score
                FROM Jobs j
                JOIN Recruiters r ON j.recruiter_id = r.recruiter_id
                LEFT JOIN Applications a ON j.job_id = a.job_id
                WHERE j.status = 'Open'
                AND j.job_id NOT IN (
                    SELECT job_id FROM Applications WHERE candidate_id = %s
                )
                GROUP BY j.job_id, j.title, j.department, j.location, j.created_at, r.full_name, r.company
                ORDER BY j.created_at DESC
                LIMIT 10
            """

        cursor.execute(query, (candidate_id,))
        recommendations = cursor.fetchall()

        return jsonify({
            'recommendations': recommendations,
            'candidate_id': candidate_id,
            'total_recommendations': len(recommendations)
        }), 200

    except Exception as e:
        logger.error(f"Job recommendations error: {str(e)}")
        return jsonify({'error': str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

@app.route('/analytics/recruiter/<int:recruiter_id>', methods=['GET'])
def get_recruiter_analytics(recruiter_id):
    """
    Advanced analytics for recruiters.

    Returns comprehensive statistics about jobs, applications, and performance.
    """
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        if connection is None:
            return jsonify({'error': 'Database connection failed'}), 500

        cursor = connection.cursor(dictionary=True)

        # Job statistics
        cursor.execute("""
            SELECT
                COUNT(*) as total_jobs,
                SUM(CASE WHEN status = 'Open' THEN 1 ELSE 0 END) as open_jobs,
                SUM(CASE WHEN status = 'Closed' THEN 1 ELSE 0 END) as closed_jobs,
                AVG(application_count) as avg_applications_per_job
            FROM (
                SELECT j.job_id, j.status, COUNT(a.application_id) as application_count
                FROM Jobs j
                LEFT JOIN Applications a ON j.job_id = a.job_id
                WHERE j.recruiter_id = %s
                GROUP BY j.job_id, j.status
            ) job_stats
        """, (recruiter_id,))

        job_stats = cursor.fetchone()

        # Application statistics by status
        cursor.execute("""
            SELECT
                COUNT(*) as total_applications,
                SUM(CASE WHEN status = 'Applied' THEN 1 ELSE 0 END) as applied,
                SUM(CASE WHEN status = 'Screening' THEN 1 ELSE 0 END) as screening,
                SUM(CASE WHEN status = 'Interviewing' THEN 1 ELSE 0 END) as interviewing,
                SUM(CASE WHEN status = 'Rejected' THEN 1 ELSE 0 END) as rejected,
                SUM(CASE WHEN status = 'Hired' THEN 1 ELSE 0 END) as hired
            FROM Applications a
            JOIN Jobs j ON a.job_id = j.job_id
            WHERE j.recruiter_id = %s
        """, (recruiter_id,))

        app_stats = cursor.fetchone()

        # Interview statistics
        cursor.execute("""
            SELECT
                COUNT(*) as total_interviews,
                SUM(CASE WHEN status = 'Scheduled' THEN 1 ELSE 0 END) as scheduled,
                SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'No-Show' THEN 1 ELSE 0 END) as no_show,
                SUM(CASE WHEN status = 'Cancelled' THEN 1 ELSE 0 END) as cancelled
            FROM Interviews i
            JOIN Applications a ON i.application_id = a.application_id
            JOIN Jobs j ON a.job_id = j.job_id
            WHERE j.recruiter_id = %s
        """, (recruiter_id,))

        interview_stats = cursor.fetchone()

        # Monthly trends (last 6 months)
        cursor.execute("""
            SELECT
                DATE_FORMAT(j.created_at, '%Y-%m') as month,
                COUNT(DISTINCT j.job_id) as jobs_posted,
                COUNT(a.application_id) as applications_received
            FROM Jobs j
            LEFT JOIN Applications a ON j.job_id = a.job_id
            WHERE j.recruiter_id = %s
            AND j.created_at >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
            GROUP BY DATE_FORMAT(j.created_at, '%Y-%m')
            ORDER BY month DESC
        """, (recruiter_id,))

        monthly_trends = cursor.fetchall()

        # Top performing jobs
        cursor.execute("""
            SELECT
                j.job_id, j.title, j.department, j.location,
                COUNT(a.application_id) as application_count,
                COUNT(CASE WHEN a.status = 'Hired' THEN 1 END) as hires
            FROM Jobs j
            LEFT JOIN Applications a ON j.job_id = a.job_id
            WHERE j.recruiter_id = %s
            GROUP BY j.job_id, j.title, j.department, j.location
            ORDER BY application_count DESC
            LIMIT 5
        """, (recruiter_id,))

        top_jobs = cursor.fetchall()

        return jsonify({
            'recruiter_id': recruiter_id,
            'job_statistics': job_stats,
            'application_statistics': app_stats,
            'interview_statistics': interview_stats,
            'monthly_trends': monthly_trends,
            'top_performing_jobs': top_jobs,
            'generated_at': datetime.now().isoformat()
        }), 200

    except Exception as e:
        logger.error(f"Recruiter analytics error: {str(e)}")
        return jsonify({'error': str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

@app.route('/bulk/jobs', methods=['POST'])
def bulk_create_jobs():
    """
    Bulk create multiple job postings.

    Expected JSON data:
        - jobs: Array of job objects
        - recruiter_id: ID of the recruiter (can be overridden per job)

    Each job object should contain:
        - title, department, location, recruiter_id (optional)
    """
    connection = None
    cursor = None

    try:
        data = request.get_json() or {}

        if 'jobs' not in data or not isinstance(data['jobs'], list):
            return jsonify({'error': 'Missing or invalid jobs array'}), 400

        jobs = data['jobs']
        if not jobs:
            return jsonify({'error': 'Jobs array cannot be empty'}), 400

        if len(jobs) > 50:  # Limit bulk operations
            return jsonify({'error': 'Maximum 50 jobs allowed in bulk operation'}), 400

        default_recruiter_id = data.get('recruiter_id')

        connection = get_db_connection()
        if connection is None:
            return jsonify({'error': 'Database connection failed'}), 500

        cursor = connection.cursor()

        successful_jobs = []
        failed_jobs = []

        for i, job_data in enumerate(jobs):
            try:
                # Validate required fields
                title = job_data.get('title', '').strip()
                department = job_data.get('department', '').strip()
                location = job_data.get('location', '').strip()
                recruiter_id = job_data.get('recruiter_id', default_recruiter_id)

                if not all([title, department, location, recruiter_id]):
                    failed_jobs.append({
                        'index': i,
                        'error': 'Missing required fields: title, department, location, recruiter_id'
                    })
                    continue

                # Insert job
                sql = """
                    INSERT INTO Jobs (recruiter_id, title, department, location)
                    VALUES (%s, %s, %s, %s)
                """
                cursor.execute(sql, (recruiter_id, title, department, location))

                successful_jobs.append({
                    'index': i,
                    'job_id': cursor.lastrowid,
                    'title': title
                })

            except Exception as e:
                failed_jobs.append({
                    'index': i,
                    'error': str(e)
                })

        connection.commit()

        return jsonify({
            'message': f'Bulk job creation completed',
            'successful': len(successful_jobs),
            'failed': len(failed_jobs),
            'successful_jobs': successful_jobs,
            'failed_jobs': failed_jobs
        }), 201

    except Exception as e:
        if connection:
            connection.rollback()
        logger.error(f"Bulk job creation error: {str(e)}")
        return jsonify({'error': str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

@app.route('/bulk/applications/status', methods=['PUT'])
def bulk_update_application_status():
    """
    Bulk update application statuses.

    Expected JSON data:
        - application_ids: Array of application IDs
        - status: New status for all applications
        - recruiter_id: Recruiter ID (for authorization)
    """
    connection = None
    cursor = None

    try:
        data = request.get_json() or {}

        application_ids = data.get('application_ids', [])
        new_status = data.get('status', '').strip()
        recruiter_id = data.get('recruiter_id')

        if not application_ids or not isinstance(application_ids, list):
            return jsonify({'error': 'Missing or invalid application_ids array'}), 400

        if new_status not in ALLOWED_APPLICATION_STATUSES:
            return jsonify({'error': f'Invalid status. Allowed: {", ".join(ALLOWED_APPLICATION_STATUSES)}'}), 400

        if not recruiter_id:
            return jsonify({'error': 'Missing recruiter_id'}), 400

        if len(application_ids) > 100:  # Limit bulk operations
            return jsonify({'error': 'Maximum 100 applications allowed in bulk operation'}), 400

        connection = get_db_connection()
        if connection is None:
            return jsonify({'error': 'Database connection failed'}), 500

        cursor = connection.cursor()

        # Verify recruiter owns these applications
        placeholders = ','.join(['%s'] * len(application_ids))
        cursor.execute(f"""
            SELECT COUNT(*) as count
            FROM Applications a
            JOIN Jobs j ON a.job_id = j.job_id
            WHERE a.application_id IN ({placeholders})
            AND j.recruiter_id = %s
        """, application_ids + [recruiter_id])

        result = cursor.fetchone()
        if result[0] != len(application_ids):
            return jsonify({'error': 'Unauthorized: Some applications do not belong to this recruiter'}), 403

        # Update statuses
        update_sql = f"""
            UPDATE Applications
            SET status = %s, updated_at = CURRENT_TIMESTAMP
            WHERE application_id IN ({placeholders})
        """
        cursor.execute(update_sql, [new_status] + application_ids)

        connection.commit()

        return jsonify({
            'message': f'Successfully updated {cursor.rowcount} applications to status: {new_status}',
            'updated_count': cursor.rowcount,
            'new_status': new_status
        }), 200

    except Exception as e:
        if connection:
            connection.rollback()
        logger.error(f"Bulk application status update error: {str(e)}")
        return jsonify({'error': str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

@app.route('/users/activity/<int:user_id>', methods=['GET'])
def get_user_activity(user_id):
    """
    Get detailed activity log for a user.

    Returns recent actions, login history, and engagement metrics.
    """
    connection = None
    cursor = None

    try:
        # Get query parameters
        limit = int(request.args.get('limit', 20))
        offset = int(request.args.get('offset', 0))

        connection = get_db_connection()
        if connection is None:
            return jsonify({'error': 'Database connection failed'}), 500

        cursor = connection.cursor(dictionary=True)

        # Get user basic info
        cursor.execute("""
            SELECT u.user_id, u.full_name, u.email, u.role, u.created_at,
                   CASE
                       WHEN u.role = 'candidate' THEN c.candidate_id
                       WHEN u.role = 'recruiter' THEN r.recruiter_id
                   END as profile_id
            FROM Users u
            LEFT JOIN Candidates c ON u.candidate_id = c.candidate_id
            LEFT JOIN Recruiters r ON u.recruiter_id = r.recruiter_id
            WHERE u.user_id = %s
        """, (user_id,))

        user_info = cursor.fetchone()
        if not user_info:
            return jsonify({'error': 'User not found'}), 404

        activities = []

        if user_info['role'] == 'candidate':
            # Candidate activities
            cursor.execute("""
                SELECT 'application' as activity_type,
                       CONCAT('Applied for job: ', j.title) as description,
                       a.created_at as activity_date,
                       a.status as status
                FROM Applications a
                JOIN Jobs j ON a.job_id = j.job_id
                WHERE a.candidate_id = %s
                ORDER BY a.created_at DESC
                LIMIT %s OFFSET %s
            """, (user_info['profile_id'], limit, offset))

            activities.extend(cursor.fetchall())

        elif user_info['role'] == 'recruiter':
            # Recruiter activities
            cursor.execute("""
                SELECT 'job_posted' as activity_type,
                       CONCAT('Posted job: ', j.title) as description,
                       j.created_at as activity_date,
                       j.status as status
                FROM Jobs j
                WHERE j.recruiter_id = %s
                ORDER BY j.created_at DESC
                LIMIT %s OFFSET %s
            """, (user_info['profile_id'], limit, offset))

            activities.extend(cursor.fetchall())

        # Get activity summary
        cursor.execute("""
            SELECT
                COUNT(CASE WHEN activity_type = 'application' THEN 1 END) as total_applications,
                COUNT(CASE WHEN activity_type = 'job_posted' THEN 1 END) as total_jobs_posted,
                MAX(activity_date) as last_activity
            FROM (
                SELECT 'application' as activity_type, a.created_at as activity_date
                FROM Applications a WHERE a.candidate_id = %s
                UNION ALL
                SELECT 'job_posted' as activity_type, j.created_at as activity_date
                FROM Jobs j WHERE j.recruiter_id = %s
            ) combined_activities
        """, (user_info.get('profile_id'), user_info.get('profile_id')))

        summary = cursor.fetchone()

        return jsonify({
            'user': user_info,
            'activities': activities,
            'summary': summary,
            'pagination': {
                'limit': limit,
                'offset': offset,
                'has_more': len(activities) == limit
            }
        }), 200

    except Exception as e:
        logger.error(f"User activity error: {str(e)}")
        return jsonify({'error': str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

@app.route('/system/stats', methods=['GET'])
def get_system_statistics():
    """
    Get overall system statistics.

    Returns aggregated data about users, jobs, applications, etc.
    Requires admin privileges (not implemented in this demo).
    """
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        if connection is None:
            return jsonify({'error': 'Database connection failed'}), 500

        cursor = connection.cursor(dictionary=True)

        # User statistics
        cursor.execute("""
            SELECT
                COUNT(*) as total_users,
                SUM(CASE WHEN role = 'candidate' THEN 1 ELSE 0 END) as total_candidates,
                SUM(CASE WHEN role = 'recruiter' THEN 1 ELSE 0 END) as total_recruiters
            FROM Users
        """)

        user_stats = cursor.fetchone()

        # Job statistics
        cursor.execute("""
            SELECT
                COUNT(*) as total_jobs,
                SUM(CASE WHEN status = 'Open' THEN 1 ELSE 0 END) as open_jobs,
                SUM(CASE WHEN status = 'Closed' THEN 1 ELSE 0 END) as closed_jobs,
                AVG(app_count) as avg_applications_per_job
            FROM (
                SELECT j.status, COUNT(a.application_id) as app_count
                FROM Jobs j
                LEFT JOIN Applications a ON j.job_id = a.job_id
                GROUP BY j.job_id, j.status
            ) job_apps
        """)

        job_stats = cursor.fetchone()

        # Application statistics
        cursor.execute("""
            SELECT
                COUNT(*) as total_applications,
                SUM(CASE WHEN status = 'Applied' THEN 1 ELSE 0 END) as applied,
                SUM(CASE WHEN status = 'Screening' THEN 1 ELSE 0 END) as screening,
                SUM(CASE WHEN status = 'Interviewing' THEN 1 ELSE 0 END) as interviewing,
                SUM(CASE WHEN status = 'Rejected' THEN 1 ELSE 0 END) as rejected,
                SUM(CASE WHEN status = 'Hired' THEN 1 ELSE 0 END) as hired
            FROM Applications
        """)

        app_stats = cursor.fetchone()

        # Recent activity (last 30 days)
        cursor.execute("""
            SELECT
                COUNT(DISTINCT j.job_id) as jobs_last_30_days,
                COUNT(DISTINCT a.application_id) as applications_last_30_days,
                COUNT(DISTINCT u.user_id) as users_last_30_days
            FROM Jobs j
            CROSS JOIN Applications a
            CROSS JOIN Users u
            WHERE j.created_at >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
               OR a.created_at >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
               OR u.created_at >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
        """)

        recent_activity = cursor.fetchone()

        return jsonify({
            'user_statistics': user_stats,
            'job_statistics': job_stats,
            'application_statistics': app_stats,
            'recent_activity': recent_activity,
            'generated_at': datetime.now().isoformat()
        }), 200

    except Exception as e:
        logger.error(f"System statistics error: {str(e)}")
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
        data = request.get_json() or {}
        
        # Validate required fields
        if 'candidate_id' not in data or 'job_id' not in data:
            return jsonify({'error': 'Missing required fields: candidate_id and job_id'}), 400

        candidate_id = data['candidate_id']
        job_id = data['job_id']
        
        connection = get_db_connection()
        if connection is None:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT application_id
            FROM Applications
            WHERE job_id = %s AND candidate_id = %s
            LIMIT 1
            """,
            (job_id, candidate_id)
        )

        if cursor.fetchone() is not None:
            return jsonify({'error': 'You have already applied for this job'}), 409
        
        # Insert application
        sql = """
            INSERT INTO Applications (job_id, candidate_id, status)
            VALUES (%s, %s, 'Applied')
        """
        values = (job_id, candidate_id)
        
        cursor.execute(sql, values)
        connection.commit()
        
        return jsonify({
            'message': 'Application submitted successfully',
            'application_id': cursor.lastrowid
        }), 201
        
    except IntegrityError as e:
        if connection:
            connection.rollback()
        return jsonify({'error': format_integrity_error(e)}), 409

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
    Update the status of an application and log to StatusHistory.

    Expected JSON data:
        - status: New application status
        - changed_by: User ID making the change (optional, defaults to system)
        - change_reason: Reason for the change (optional)

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

        changed_by = data.get('changed_by', 1)
        change_reason = data.get('change_reason', f'Status changed to {new_status}')

        connection = get_db_connection()
        if connection is None:
            return jsonify({'error': 'Database connection failed'}), 500

        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            "SELECT application_id, status FROM Applications WHERE application_id = %s",
            (app_id,)
        )
        result = cursor.fetchone()
        if result is None:
            return jsonify({'error': 'Application not found'}), 404

        old_status = result['status']

        sql = """
            UPDATE Applications
            SET status = %s
            WHERE application_id = %s
        """
        values = (new_status, app_id)

        cursor.execute(sql, values)

        # Log to status history
        cursor.execute("""
            INSERT INTO StatusHistory (application_id, old_status, new_status, changed_by, change_reason)
            VALUES (%s, %s, %s, %s, %s)
        """, (app_id, old_status, new_status, changed_by, change_reason))

        connection.commit()

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

@app.route('/interviews', methods=['POST'])
def schedule_interview():
    """
    Schedule a new interview for an application.

    Expected JSON data:
        - application_id: Application ID
        - scheduled_at: Datetime string
        - interview_type: Phone, Video, or Onsite
    """
    connection = None
    cursor = None

    try:
        data = request.get_json() or {}

        required_fields = ['application_id', 'scheduled_at', 'interview_type']
        for field in required_fields:
            if field not in data or str(data[field]).strip() == '':
                return jsonify({'error': f'Missing required field: {field}'}), 400

        application_id = data['application_id']
        interview_type = str(data['interview_type']).strip()
        raw_scheduled_at = str(data['scheduled_at']).strip()

        if interview_type not in ALLOWED_INTERVIEW_TYPES:
            return jsonify({'error': 'Invalid interview_type value'}), 400

        try:
            parsed_dt = datetime.fromisoformat(raw_scheduled_at.replace(' ', 'T'))
            scheduled_at_sql = parsed_dt.strftime('%Y-%m-%d %H:%M:%S')
        except ValueError:
            return jsonify({'error': 'Invalid scheduled_at format'}), 400

        connection = get_db_connection()
        if connection is None:
            return jsonify({'error': 'Database connection failed'}), 500

        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT a.application_id, a.status
            FROM Applications a
            WHERE a.application_id = %s
            """,
            (application_id,)
        )
        application = cursor.fetchone()

        if application is None:
            return jsonify({'error': 'Application not found'}), 404

        if application['status'] in {'Rejected', 'Hired'}:
            return jsonify({'error': 'Cannot schedule interview for closed application'}), 400

        cursor.execute(
            """
            INSERT INTO Interviews (application_id, scheduled_at, interview_type)
            VALUES (%s, %s, %s)
            """,
            (application_id, scheduled_at_sql, interview_type)
        )
        connection.commit()

        return jsonify({
            'message': 'Interview scheduled successfully',
            'interview_id': cursor.lastrowid
        }), 201

    except IntegrityError as e:
        if connection:
            connection.rollback()
        return jsonify({'error': format_integrity_error(e)}), 409

    except Exception as e:
        if connection:
            connection.rollback()
        return jsonify({'error': str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

@app.route('/interviews/<int:interview_id>/status', methods=['PUT'])
def update_interview_status(interview_id):
    """
    Update status for an interview.

    Expected JSON data:
        - status: Scheduled, Completed, No-Show, Cancelled
    """
    connection = None
    cursor = None

    try:
        data = request.get_json() or {}
        new_status = str(data.get('status', '')).strip()

        if new_status not in ALLOWED_INTERVIEW_STATUSES:
            return jsonify({'error': 'Invalid interview status value'}), 400

        connection = get_db_connection()
        if connection is None:
            return jsonify({'error': 'Database connection failed'}), 500

        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT interview_id FROM Interviews WHERE interview_id = %s",
            (interview_id,)
        )
        if cursor.fetchone() is None:
            return jsonify({'error': 'Interview not found'}), 404

        cursor.execute(
            """
            UPDATE Interviews
            SET status = %s
            WHERE interview_id = %s
            """,
            (new_status, interview_id)
        )
        connection.commit()

        return jsonify({'message': 'Interview status updated successfully'}), 200

    except IntegrityError as e:
        if connection:
            connection.rollback()
        return jsonify({'error': format_integrity_error(e)}), 409

    except Exception as e:
        if connection:
            connection.rollback()
        return jsonify({'error': str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

@app.route('/interviews/scheduled/recruiter/<int:recruiter_id>', methods=['GET'])
def get_scheduled_interviews_for_recruiter(recruiter_id):
    """
    Fetch scheduled interviews for a recruiter's jobs.

    This query targets the Scheduled_Interviews SQL view. If the view is
    unavailable, it falls back to the Interviews table with status filtering.
    """
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        if connection is None:
            return jsonify({'error': 'Database connection failed'}), 500

        cursor = connection.cursor(dictionary=True)

        view_sql = """
            SELECT
                si.interview_id,
                i.application_id,
                c.full_name AS candidate_name,
                c.email AS candidate_email,
                j.title AS job_title,
                si.scheduled_at,
                si.interview_type,
                i.status
            FROM Scheduled_Interviews si
            INNER JOIN Interviews i ON si.interview_id = i.interview_id
            INNER JOIN Applications a ON i.application_id = a.application_id
            INNER JOIN Candidates c ON a.candidate_id = c.candidate_id
            INNER JOIN Jobs j ON a.job_id = j.job_id
            WHERE j.recruiter_id = %s
            ORDER BY si.scheduled_at ASC
        """

        fallback_sql = """
            SELECT
                i.interview_id,
                i.application_id,
                c.full_name AS candidate_name,
                c.email AS candidate_email,
                j.title AS job_title,
                i.scheduled_at,
                i.interview_type,
                i.status
            FROM Interviews i
            INNER JOIN Applications a ON i.application_id = a.application_id
            INNER JOIN Candidates c ON a.candidate_id = c.candidate_id
            INNER JOIN Jobs j ON a.job_id = j.job_id
            WHERE j.recruiter_id = %s AND i.status = 'Scheduled'
            ORDER BY i.scheduled_at ASC
        """

        try:
            cursor.execute(view_sql, (recruiter_id,))
        except Exception:
            cursor.execute(fallback_sql, (recruiter_id,))

        interviews = cursor.fetchall()
        return jsonify(interviews), 200

    except Exception as e:
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

@app.route('/applications/recruiter/<int:recruiter_id>', methods=['GET'])
def get_recruiter_applications(recruiter_id):
    """
    Fetch all applications for jobs owned by a specific recruiter.

    Args:
        recruiter_id: Recruiter ID

    Returns:
        JSON list of applications scoped to recruiter jobs
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
                c.candidate_id,
                c.full_name AS candidate_name,
                c.email AS candidate_email,
                j.job_id,
                j.title AS job_title,
                j.department,
                j.location,
                a.status,
                a.created_at
            FROM Applications a
            INNER JOIN Candidates c ON a.candidate_id = c.candidate_id
            INNER JOIN Jobs j ON a.job_id = j.job_id
            WHERE j.recruiter_id = %s
            ORDER BY a.created_at DESC
        """

        cursor.execute(sql, (recruiter_id,))
        applications = cursor.fetchall()
        return jsonify(applications), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

@app.route('/candidates/recruiter/<int:recruiter_id>', methods=['GET'])
def get_recruiter_candidates(recruiter_id):
    """
    Fetch distinct candidates who applied to jobs owned by a specific recruiter.

    Args:
        recruiter_id: Recruiter ID

    Returns:
        JSON list of candidate summaries
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
                c.candidate_id,
                c.full_name,
                c.email,
                c.phone,
                COUNT(a.application_id) AS applications_count,
                MAX(a.created_at) AS latest_application_at
            FROM Candidates c
            INNER JOIN Applications a ON c.candidate_id = a.candidate_id
            INNER JOIN Jobs j ON a.job_id = j.job_id
            WHERE j.recruiter_id = %s
            GROUP BY c.candidate_id, c.full_name, c.email, c.phone
            ORDER BY latest_application_at DESC
        """

        cursor.execute(sql, (recruiter_id,))
        candidates = cursor.fetchall()
        return jsonify(candidates), 200

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

# =============================================
# Interview Feedback Endpoints
# =============================================

@app.route('/interviews/<int:interview_id>/feedback', methods=['POST'])
def submit_interview_feedback(interview_id):
    """
    Submit feedback for an interview.
    Creates InterviewFeedback record and optionally updates application status.
    """
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        if connection is None:
            return jsonify({'error': 'Database connection failed'}), 500

        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400

        recruiter_id = data.get('recruiter_id')
        rating = data.get('rating')
        technical_rating = data.get('technical_rating')
        communication_rating = data.get('communication_rating')
        culture_fit_rating = data.get('culture_fit_rating')
        strengths = data.get('strengths', '')
        concerns = data.get('concerns', '')
        recommendation = data.get('recommendation')
        additional_notes = data.get('additional_notes', '')
        new_status = data.get('new_status')

        if not all([recruiter_id, rating, recommendation]):
            return jsonify({'error': 'rating and recommendation are required'}), 400

        if rating and (rating < 1 or rating > 5):
            return jsonify({'error': 'Rating must be between 1 and 5'}), 400

        if recommendation not in ['Strong Hire', 'Hire', 'No Hire', 'Strong No Hire']:
            return jsonify({'error': 'Invalid recommendation value'}), 400

        cursor = connection.cursor(dictionary=True)

        # Check if feedback already exists
        cursor.execute("SELECT feedback_id FROM InterviewFeedback WHERE interview_id = %s", (interview_id,))
        if cursor.fetchone():
            return jsonify({'error': 'Feedback already submitted for this interview'}), 409

        # Verify interview exists and get application_id
        cursor.execute("""
            SELECT i.interview_id, i.application_id, a.candidate_id, j.recruiter_id
            FROM Interviews i
            JOIN Applications a ON i.application_id = a.application_id
            JOIN Jobs j ON a.job_id = j.job_id
            WHERE i.interview_id = %s
        """, (interview_id,))
        interview = cursor.fetchone()
        if not interview:
            return jsonify({'error': 'Interview not found'}), 404

        # Insert feedback
        cursor.execute("""
            INSERT INTO InterviewFeedback
            (interview_id, recruiter_id, rating, technical_rating, communication_rating,
             culture_fit_rating, strengths, concerns, recommendation, additional_notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (interview_id, recruiter_id, rating, technical_rating, communication_rating,
              culture_fit_rating, strengths, concerns, recommendation, additional_notes))

        # Update interview status to Completed
        cursor.execute(
            "UPDATE Interviews SET status = 'Completed' WHERE interview_id = %s",
            (interview_id,)
        )

        # Update application status if new_status provided
        if new_status and new_status in ALLOWED_APPLICATION_STATUSES:
            cursor.execute(
                "UPDATE Applications SET status = %s WHERE application_id = %s",
                (new_status, interview['application_id'])
            )

            # Log status change in history
            cursor.execute("""
                INSERT INTO StatusHistory (application_id, old_status, new_status, changed_by, change_reason)
                SELECT application_id, status, %s, %s, %s
                FROM Applications WHERE application_id = %s
            """, (new_status, recruiter_id, f'Interview feedback: {recommendation}', interview['application_id']))

        connection.commit()

        return jsonify({
            'message': 'Feedback submitted successfully',
            'feedback_id': cursor.lastrowid,
            'recommendation': recommendation
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


@app.route('/interviews/<int:interview_id>/feedback', methods=['GET'])
def get_interview_feedback(interview_id):
    """Get feedback for a specific interview."""
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        if connection is None:
            return jsonify({'error': 'Database connection failed'}), 500

        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT f.*, r.full_name AS recruiter_name, r.company
            FROM InterviewFeedback f
            JOIN Recruiters r ON f.recruiter_id = r.recruiter_id
            WHERE f.interview_id = %s
        """, (interview_id,))

        feedback = cursor.fetchone()

        if not feedback:
            return jsonify({'error': 'Feedback not found'}), 404

        return jsonify(feedback), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


# =============================================
# Candidate Rating Endpoints
# =============================================

@app.route('/applications/<int:application_id>/rating', methods=['PUT'])
def rate_application(application_id):
    """
    Rate a candidate's application (1-5 stars with notes).
    One rating per recruiter per application.
    """
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        if connection is None:
            return jsonify({'error': 'Database connection failed'}), 500

        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400

        recruiter_id = data.get('recruiter_id')
        rating = data.get('rating')
        review_notes = data.get('review_notes', '')

        if not all([recruiter_id, rating]):
            return jsonify({'error': 'recruiter_id and rating are required'}), 400

        if rating < 1 or rating > 5:
            return jsonify({'error': 'Rating must be between 1 and 5'}), 400

        cursor = connection.cursor(dictionary=True)

        # Verify application exists
        cursor.execute(
            "SELECT application_id FROM Applications WHERE application_id = %s",
            (application_id,)
        )
        if not cursor.fetchone():
            return jsonify({'error': 'Application not found'}), 404

        # Upsert rating (update if exists, insert if not)
        cursor.execute("""
            INSERT INTO ApplicationRatings (application_id, recruiter_id, rating, review_notes)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                rating = VALUES(rating),
                review_notes = VALUES(review_notes),
                rated_at = CURRENT_TIMESTAMP
        """, (application_id, recruiter_id, rating, review_notes))

        connection.commit()

        return jsonify({
            'message': 'Rating saved successfully',
            'rating': rating
        }), 200

    except Exception as e:
        if connection:
            connection.rollback()
        return jsonify({'error': str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


@app.route('/applications/<int:application_id>/rating', methods=['GET'])
def get_application_rating(application_id):
    """Get rating for an application by a specific recruiter."""
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        if connection is None:
            return jsonify({'error': 'Database connection failed'}), 500

        recruiter_id = request.args.get('recruiter_id')

        cursor = connection.cursor(dictionary=True)

        if recruiter_id:
            cursor.execute("""
                SELECT ar.*, r.full_name AS recruiter_name
                FROM ApplicationRatings ar
                JOIN Recruiters r ON ar.recruiter_id = r.recruiter_id
                WHERE ar.application_id = %s AND ar.recruiter_id = %s
            """, (application_id, recruiter_id))
            rating = cursor.fetchone()
            if not rating:
                return jsonify({'error': 'Rating not found'}), 404
            return jsonify(rating), 200
        else:
            # Get all ratings for this application
            cursor.execute("""
                SELECT ar.*, r.full_name AS recruiter_name
                FROM ApplicationRatings ar
                JOIN Recruiters r ON ar.recruiter_id = r.recruiter_id
                WHERE ar.application_id = %s
                ORDER BY ar.rated_at DESC
            """, (application_id,))
            ratings = cursor.fetchall()

            avg_rating = sum(r['rating'] for r in ratings) / len(ratings) if ratings else None

            return jsonify({
                'ratings': ratings,
                'average_rating': round(avg_rating, 1) if avg_rating else None,
                'total_ratings': len(ratings)
            }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


# =============================================
# Status History Endpoints
# =============================================

@app.route('/applications/<int:application_id>/history', methods=['GET'])
def get_application_history(application_id):
    """Get complete status history for an application."""
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        if connection is None:
            return jsonify({'error': 'Database connection failed'}), 500

        cursor = connection.cursor(dictionary=True)

        # Get status history
        cursor.execute("""
            SELECT sh.*, u.full_name AS changed_by_name, u.role AS changed_by_role
            FROM StatusHistory sh
            JOIN Users u ON sh.changed_by = u.user_id
            WHERE sh.application_id = %s
            ORDER BY sh.changed_at ASC
        """, (application_id,))
        history = cursor.fetchall()

        # Get current application status
        cursor.execute("""
            SELECT a.*, c.full_name AS candidate_name, j.title AS job_title
            FROM Applications a
            JOIN Candidates c ON a.candidate_id = c.candidate_id
            JOIN Jobs j ON a.job_id = j.job_id
            WHERE a.application_id = %s
        """, (application_id,))
        application = cursor.fetchone()

        if not application:
            return jsonify({'error': 'Application not found'}), 404

        return jsonify({
            'application': application,
            'history': history
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


@app.route('/applications/<int:application_id>/status', methods=['PUT'])
def update_application_status_v2(application_id):
    """
    Update application status with optional reason.
    Logs the change to StatusHistory.
    """
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        if connection is None:
            return jsonify({'error': 'Database connection failed'}), 500

        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400

        new_status = data.get('status')
        changed_by = data.get('changed_by')
        change_reason = data.get('change_reason', '')

        if not all([new_status, changed_by]):
            return jsonify({'error': 'status and changed_by are required'}), 400

        if new_status not in ALLOWED_APPLICATION_STATUSES:
            return jsonify({'error': f'Invalid status. Must be one of: {", ".join(ALLOWED_APPLICATION_STATUSES)}'}), 400

        cursor = connection.cursor(dictionary=True)

        # Get current status
        cursor.execute(
            "SELECT status FROM Applications WHERE application_id = %s",
            (application_id,)
        )
        result = cursor.fetchone()
        if not result:
            return jsonify({'error': 'Application not found'}), 404

        old_status = result['status']

        # Update status
        cursor.execute(
            "UPDATE Applications SET status = %s WHERE application_id = %s",
            (new_status, application_id)
        )

        # Log to history
        cursor.execute("""
            INSERT INTO StatusHistory (application_id, old_status, new_status, changed_by, change_reason)
            VALUES (%s, %s, %s, %s, %s)
        """, (application_id, old_status, new_status, changed_by, change_reason))

        connection.commit()

        return jsonify({
            'message': 'Status updated successfully',
            'old_status': old_status,
            'new_status': new_status
        }), 200

    except Exception as e:
        if connection:
            connection.rollback()
        return jsonify({'error': str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


# =============================================
# Dashboard Analytics Endpoints
# =============================================

@app.route('/dashboard/recruiter/<int:recruiter_id>', methods=['GET'])
def get_recruiter_dashboard(recruiter_id):
    """
    Get comprehensive recruiter dashboard data including:
    - Job statistics
    - Application counts by status
    - Recent interviews
    - Top candidates by rating
    """
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        if connection is None:
            return jsonify({'error': 'Database connection failed'}), 500

        cursor = connection.cursor(dictionary=True)

        # Get jobs count
        cursor.execute(
            "SELECT COUNT(*) as count FROM Jobs WHERE recruiter_id = %s",
            (recruiter_id,)
        )
        jobs_count = cursor.fetchone()['count']

        # Get applications by status
        cursor.execute("""
            SELECT a.status, COUNT(*) as count
            FROM Applications a
            JOIN Jobs j ON a.job_id = j.job_id
            WHERE j.recruiter_id = %s
            GROUP BY a.status
        """, (recruiter_id,))
        status_counts = {row['status']: row['count'] for row in cursor.fetchall()}

        # Get total applications
        total_apps = sum(status_counts.values())

        # Get scheduled interviews
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM Interviews i
            JOIN Applications a ON i.application_id = a.application_id
            JOIN Jobs j ON a.job_id = j.job_id
            WHERE j.recruiter_id = %s AND i.status = 'Scheduled'
        """, (recruiter_id,))
        scheduled_interviews = cursor.fetchone()['count']

        # Get top rated candidates
        cursor.execute("""
            SELECT a.application_id, c.full_name, c.email, j.title AS job_title,
                   AVG(ar.rating) as avg_rating, COUNT(ar.rating_id) as rating_count
            FROM Applications a
            JOIN Candidates c ON a.candidate_id = c.candidate_id
            JOIN Jobs j ON a.job_id = j.job_id
            JOIN ApplicationRatings ar ON a.application_id = ar.application_id
            WHERE j.recruiter_id = %s
            GROUP BY a.application_id
            ORDER BY avg_rating DESC
            LIMIT 5
        """, (recruiter_id,))
        top_candidates = cursor.fetchall()

        # Recent interviews with feedback
        cursor.execute("""
            SELECT i.interview_id, i.scheduled_at, i.interview_type, i.status,
                   c.full_name AS candidate_name, j.title AS job_title,
                   f.feedback_id, f.recommendation, f.rating
            FROM Interviews i
            JOIN Applications a ON i.application_id = a.application_id
            JOIN Candidates c ON a.candidate_id = c.candidate_id
            JOIN Jobs j ON a.job_id = j.job_id
            LEFT JOIN InterviewFeedback f ON i.interview_id = f.interview_id
            WHERE j.recruiter_id = %s
            ORDER BY i.scheduled_at DESC
            LIMIT 10
        """, (recruiter_id,))
        recent_interviews = cursor.fetchall()

        return jsonify({
            'jobs_count': jobs_count,
            'total_applications': total_apps,
            'applications_by_status': status_counts,
            'scheduled_interviews': scheduled_interviews,
            'top_candidates': top_candidates,
            'recent_interviews': recent_interviews
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


if __name__ == '__main__':
    initialize_auth_table()
    initialize_interview_artifacts()
    app.run(debug=True, port=5001)
