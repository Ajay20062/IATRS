from contextlib import contextmanager
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from db_connect import get_db_connection

app = Flask(__name__)
CORS(app)

VALID_TABLES = {
    "recruiters": "Recruiters",
    "jobs": "Jobs",
    "candidates": "Candidates",
    "applications": "Applications",
    "interviews": "Interviews",
}

FRONTEND_DIR = Path(__file__).parent / "frontend"


def error_response(message, status_code=400):
    return jsonify({"error": message}), status_code


def parse_json(required_fields):
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return None, error_response("Request body must be a valid JSON object", 400)

    missing = [field for field in required_fields if data.get(field) in (None, "")]
    if missing:
        return None, error_response(
            f"Missing required field(s): {', '.join(missing)}", 400
        )

    return data, None


@contextmanager
def db_cursor(dictionary=False):
    connection = get_db_connection()
    if connection is None:
        raise ConnectionError("Database connection failed")

    cursor = connection.cursor(dictionary=dictionary)
    try:
        yield connection, cursor
    finally:
        cursor.close()
        if connection.is_connected():
            connection.close()


@app.route("/")
def index():
    return jsonify(
        {
            "message": "ATS API is running successfully!",
            "frontend": {
                "candidate_portal": "/ui",
                "recruiter_dashboard": "/ui/dashboard.html",
                "database_schema": "/ui/database-schema.html",
                "api_status": "/ui/api-status.html",
            },
        }
    )


@app.route("/ui")
def serve_ui_index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/ui/<path:filename>")
def serve_ui_file(filename):
    return send_from_directory(FRONTEND_DIR, filename)

@app.route('/jobs', methods=['GET'])
def get_jobs():
    try:
        with db_cursor(dictionary=True) as (_, cursor):
            cursor.execute("SELECT * FROM Jobs ORDER BY created_at DESC")
            jobs = cursor.fetchall()
        return jsonify(jobs), 200
    except ConnectionError as exc:
        return error_response(str(exc), 500)
    except Exception as exc:
        return error_response(str(exc), 500)

@app.route('/jobs/<int:id>', methods=['GET'])
def get_job(id):
    try:
        with db_cursor(dictionary=True) as (_, cursor):
            cursor.execute("SELECT * FROM Jobs WHERE job_id = %s", (id,))
            job = cursor.fetchone()

        if job is None:
            return error_response("Job not found", 404)

        return jsonify(job), 200
    except ConnectionError as exc:
        return error_response(str(exc), 500)
    except Exception as exc:
        return error_response(str(exc), 500)

@app.route('/jobs', methods=['POST'])
def create_job():
    data, err = parse_json(["title", "department", "location", "recruiter_id"])
    if err:
        return err

    try:
        recruiter_id = int(data["recruiter_id"])
    except (TypeError, ValueError):
        return error_response("recruiter_id must be an integer", 400)

    try:
        with db_cursor() as (connection, cursor):
            sql = """
                INSERT INTO Jobs (recruiter_id, title, department, location)
                VALUES (%s, %s, %s, %s)
            """
            values = (
                recruiter_id,
                data["title"].strip(),
                data["department"].strip(),
                data["location"].strip(),
            )
            cursor.execute(sql, values)
            connection.commit()

        return jsonify({
            "message": "Job created successfully",
            "job_id": cursor.lastrowid
        }), 201
    except ConnectionError as exc:
        return error_response(str(exc), 500)
    except Exception as exc:
        return error_response(str(exc), 500)

@app.route('/apply', methods=['POST'])
def apply_for_job():
    data, err = parse_json(["candidate_id", "job_id"])
    if err:
        return err

    try:
        job_id = int(data["job_id"])
        candidate_id = int(data["candidate_id"])
    except (TypeError, ValueError):
        return error_response("candidate_id and job_id must be integers", 400)

    try:
        with db_cursor() as (connection, cursor):
            sql = """
                INSERT INTO Applications (job_id, candidate_id, status)
                VALUES (%s, %s, 'Applied')
            """
            values = (job_id, candidate_id)
            cursor.execute(sql, values)
            connection.commit()

        return jsonify({
            "message": "Application submitted successfully",
            "application_id": cursor.lastrowid
        }), 201
    except ConnectionError as exc:
        return error_response(str(exc), 500)
    except Exception as exc:
        return error_response(str(exc), 500)

@app.route('/applications', methods=['GET'])
def get_applications():
    try:
        with db_cursor(dictionary=True) as (_, cursor):
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
    except ConnectionError as exc:
        return error_response(str(exc), 500)
    except Exception as exc:
        return error_response(str(exc), 500)

@app.route('/database/stats', methods=['GET'])
def get_database_stats():
    try:
        with db_cursor(dictionary=True) as (_, cursor):
            stats = {}
            cursor.execute("SELECT COUNT(*) as count FROM Recruiters")
            stats["recruiters"] = cursor.fetchone()["count"]

            cursor.execute("SELECT status, COUNT(*) as count FROM Jobs GROUP BY status")
            jobs_by_status = cursor.fetchall()
            stats["jobs"] = {"total": sum(j["count"] for j in jobs_by_status)}
            stats["jobs_by_status"] = {j["status"]: j["count"] for j in jobs_by_status}

            cursor.execute("SELECT COUNT(*) as count FROM Candidates")
            stats["candidates"] = cursor.fetchone()["count"]

            cursor.execute(
                "SELECT status, COUNT(*) as count FROM Applications GROUP BY status"
            )
            apps_by_status = cursor.fetchall()
            stats["applications"] = {"total": sum(a["count"] for a in apps_by_status)}
            stats["applications_by_status"] = {
                a["status"]: a["count"] for a in apps_by_status
            }

            cursor.execute("SELECT COUNT(*) as count FROM Interviews")
            stats["interviews"] = cursor.fetchone()["count"]

            cursor.execute(
                "SELECT DATE(created_at) as date, COUNT(*) as count "
                "FROM Jobs WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY) "
                "GROUP BY DATE(created_at)"
            )
            stats["recent_jobs"] = cursor.fetchall()

            cursor.execute(
                "SELECT DATE(created_at) as date, COUNT(*) as count "
                "FROM Applications WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY) "
                "GROUP BY DATE(created_at)"
            )
            stats["recent_applications"] = cursor.fetchall()

        return jsonify(stats), 200
    except ConnectionError as exc:
        return error_response(str(exc), 500)
    except Exception as exc:
        return error_response(str(exc), 500)

@app.route('/database/tables', methods=['GET'])
def get_table_data():
    table_name = request.args.get("table", "").lower()

    try:
        limit = int(request.args.get("limit", 50))
        offset = int(request.args.get("offset", 0))
    except (TypeError, ValueError):
        return error_response("limit and offset must be integers", 400)

    if table_name not in VALID_TABLES:
        return error_response("Invalid table name", 400)

    if limit < 1:
        limit = 1
    if limit > 100:
        limit = 100
    if offset < 0:
        offset = 0

    table_sql_name = VALID_TABLES[table_name]

    try:
        with db_cursor(dictionary=True) as (_, cursor):
            cursor.execute(
                f"SELECT * FROM {table_sql_name} ORDER BY 1 DESC LIMIT %s OFFSET %s",
                (limit, offset),
            )
            data = cursor.fetchall()

            cursor.execute(f"SELECT COUNT(*) as total FROM {table_sql_name}")
            total = cursor.fetchone()["total"]

        return jsonify({
            "data": data,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total,
        }), 200
    except ConnectionError as exc:
        return error_response(str(exc), 500)
    except Exception as exc:
        return error_response(str(exc), 500)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
