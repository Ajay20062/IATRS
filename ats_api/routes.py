from flask import Blueprint, jsonify, request
from mysql.connector.errors import IntegrityError

from .db import Error, create_db_connection, safe_close

api_bp = Blueprint("api", __name__)
JOB_STATUSES = {"Open", "Closed", "Paused"}


def _json_error(message: str, status_code: int):
    return jsonify({"error": message}), status_code


def _parse_int(data: dict, field: str):
    value = data.get(field)
    if value is None:
        raise ValueError(f"Missing required field: {field}")
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError(f"Field '{field}' must be an integer")


def _parse_non_empty_str(data: dict, field: str):
    value = data.get(field)
    if value is None:
        raise ValueError(f"Missing required field: {field}")
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Field '{field}' must be a non-empty string")
    return value.strip()


@api_bp.route("/")
def index():
    return jsonify({"message": "ATS API is running successfully!"})


@api_bp.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "ats-api"}), 200


@api_bp.route("/jobs", methods=["GET"])
def get_jobs():
    connection = None
    cursor = None
    try:
        status = request.args.get("status")
        if status and status not in JOB_STATUSES:
            return _json_error(
                f"Invalid status '{status}'. Allowed values: {', '.join(sorted(JOB_STATUSES))}",
                400,
            )

        connection = create_db_connection()
        cursor = connection.cursor(dictionary=True)
        if status:
            cursor.execute(
                "SELECT * FROM Jobs WHERE status = %s ORDER BY created_at DESC",
                (status,),
            )
        else:
            cursor.execute("SELECT * FROM Jobs ORDER BY created_at DESC")
        jobs = cursor.fetchall()
        return jsonify(jobs), 200
    except (Error, ValueError) as exc:
        return _json_error(str(exc), 500)
    finally:
        safe_close(connection=connection, cursor=cursor)


@api_bp.route("/jobs/<int:job_id>", methods=["GET"])
def get_job(job_id: int):
    connection = None
    cursor = None
    try:
        connection = create_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Jobs WHERE job_id = %s", (job_id,))
        job = cursor.fetchone()
        if job is None:
            return _json_error("Job not found", 404)
        return jsonify(job), 200
    except (Error, ValueError) as exc:
        return _json_error(str(exc), 500)
    finally:
        safe_close(connection=connection, cursor=cursor)


@api_bp.route("/jobs", methods=["POST"])
def create_job():
    connection = None
    cursor = None
    try:
        data = request.get_json(silent=True) or {}
        title = _parse_non_empty_str(data, "title")
        department = _parse_non_empty_str(data, "department")
        location = _parse_non_empty_str(data, "location")
        recruiter_id = _parse_int(data, "recruiter_id")
        status = data.get("status", "Open")
        if status not in JOB_STATUSES:
            return _json_error(
                f"Invalid status '{status}'. Allowed values: {', '.join(sorted(JOB_STATUSES))}",
                400,
            )

        connection = create_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO Jobs (recruiter_id, title, department, location, status)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (recruiter_id, title, department, location, status),
        )
        connection.commit()
        return jsonify({"message": "Job created successfully", "job_id": cursor.lastrowid}), 201
    except ValueError as exc:
        return _json_error(str(exc), 400)
    except IntegrityError as exc:
        if connection:
            connection.rollback()
        return _json_error(f"Data integrity error: {exc.msg}", 409)
    except Error as exc:
        if connection:
            connection.rollback()
        return _json_error(str(exc), 500)
    finally:
        safe_close(connection=connection, cursor=cursor)


@api_bp.route("/apply", methods=["POST"])
def apply_for_job():
    connection = None
    cursor = None
    try:
        data = request.get_json(silent=True) or {}
        candidate_id = _parse_int(data, "candidate_id")
        job_id = _parse_int(data, "job_id")

        connection = create_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO Applications (job_id, candidate_id, status)
            VALUES (%s, %s, 'Applied')
            """,
            (job_id, candidate_id),
        )
        connection.commit()
        return jsonify(
            {
                "message": "Application submitted successfully",
                "application_id": cursor.lastrowid,
            }
        ), 201
    except ValueError as exc:
        return _json_error(str(exc), 400)
    except IntegrityError as exc:
        if connection:
            connection.rollback()
        return _json_error(f"Data integrity error: {exc.msg}", 409)
    except Error as exc:
        if connection:
            connection.rollback()
        return _json_error(str(exc), 500)
    finally:
        safe_close(connection=connection, cursor=cursor)


@api_bp.route("/applications", methods=["GET"])
def get_applications():
    connection = None
    cursor = None
    try:
        connection = create_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
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
        )
        applications = cursor.fetchall()
        return jsonify(applications), 200
    except (Error, ValueError) as exc:
        return _json_error(str(exc), 500)
    finally:
        safe_close(connection=connection, cursor=cursor)
