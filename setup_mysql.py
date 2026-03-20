import os

import mysql.connector
from mysql.connector import Error

from ats_api.config import load_db_config


def _split_sql_statements(schema_sql: str) -> list[str]:
    statements = []
    current = []
    for line in schema_sql.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        current.append(line)
        if stripped.endswith(";"):
            statements.append("\n".join(current).strip().rstrip(";"))
            current = []
    if current:
        statements.append("\n".join(current).strip().rstrip(";"))
    return statements


def _base_db_config() -> dict:
    config = load_db_config()
    required = ["host", "user", "password", "database"]
    env_name = {
        "host": "DB_HOST",
        "user": "DB_USER",
        "password": "DB_PASSWORD",
        "database": "DB_NAME",
    }
    missing = [env_name[key] for key in required if not config.get(key)]
    if missing:
        raise ValueError(f"Missing database environment variables: {', '.join(missing)}")
    return config


def create_database_if_missing(config: dict) -> None:
    connection = mysql.connector.connect(
        host=config["host"],
        port=config["port"],
        user=config["user"],
        password=config["password"],
    )
    try:
        cursor = connection.cursor()
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{config['database']}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        connection.commit()
    finally:
        cursor.close()
        connection.close()


def apply_schema(connection, schema_file_path: str) -> None:
    with open(schema_file_path, "r", encoding="utf-8") as file:
        schema_sql = file.read()

    cursor = connection.cursor()
    try:
        for statement in _split_sql_statements(schema_sql):
            cursor.execute(statement)
        connection.commit()
    finally:
        cursor.close()


def seed_data(connection) -> None:
    cursor = connection.cursor()
    try:
        recruiters = [
            ("John Smith", "john.smith@techcorp.com", "TechCorp"),
            ("Sarah Johnson", "sarah.johnson@innovate.com", "Innovate Solutions"),
            ("Michael Chen", "michael.chen@dataworks.com", "DataWorks Inc"),
            ("Emily Rodriguez", "emily.rodriguez@cloudify.com", "Cloudify"),
            ("David Kim", "david.kim@startupx.com", "StartupX"),
        ]

        cursor.executemany(
            """
            INSERT INTO Recruiters (full_name, email, company)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE
                full_name = VALUES(full_name),
                company = VALUES(company)
            """,
            recruiters,
        )

        cursor.execute("SELECT recruiter_id, email FROM Recruiters")
        recruiter_map = {email: recruiter_id for recruiter_id, email in cursor.fetchall()}

        jobs = [
            ("john.smith@techcorp.com", "Senior Python Developer", "Engineering", "San Francisco, CA", "Open"),
            ("sarah.johnson@innovate.com", "Data Scientist", "Data Analytics", "New York, NY", "Open"),
            ("michael.chen@dataworks.com", "Frontend Engineer", "Engineering", "Remote", "Open"),
            ("emily.rodriguez@cloudify.com", "DevOps Engineer", "Infrastructure", "Austin, TX", "Paused"),
            ("david.kim@startupx.com", "Product Manager", "Product", "Seattle, WA", "Open"),
        ]
        for recruiter_email, title, department, location, status in jobs:
            cursor.execute(
                """
                INSERT INTO Jobs (recruiter_id, title, department, location, status)
                SELECT %s, %s, %s, %s, %s
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM Jobs
                    WHERE recruiter_id = %s AND title = %s
                )
                """,
                (
                    recruiter_map[recruiter_email],
                    title,
                    department,
                    location,
                    status,
                    recruiter_map[recruiter_email],
                    title,
                ),
            )

        candidates = [
            ("Alice Williams", "alice.williams@email.com", "+1-555-0101", "https://resume.com/alice"),
            ("Bob Martinez", "bob.martinez@email.com", "+1-555-0102", "https://resume.com/bob"),
            ("Carol Davis", "carol.davis@email.com", "+1-555-0103", "https://resume.com/carol"),
            ("Daniel Brown", "daniel.brown@email.com", "+1-555-0104", "https://resume.com/daniel"),
            ("Eva Taylor", "eva.taylor@email.com", "+1-555-0105", "https://resume.com/eva"),
        ]
        cursor.executemany(
            """
            INSERT INTO Candidates (full_name, email, phone, resume_url)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                full_name = VALUES(full_name),
                phone = VALUES(phone),
                resume_url = VALUES(resume_url)
            """,
            candidates,
        )

        cursor.execute("SELECT job_id FROM Jobs ORDER BY job_id LIMIT 3")
        job_ids = [row[0] for row in cursor.fetchall()]

        cursor.execute("SELECT candidate_id FROM Candidates ORDER BY candidate_id LIMIT 3")
        candidate_ids = [row[0] for row in cursor.fetchall()]

        if job_ids and candidate_ids:
            for job_id, candidate_id in zip(job_ids, candidate_ids):
                cursor.execute(
                    """
                    INSERT INTO Applications (job_id, candidate_id, status)
                    VALUES (%s, %s, 'Applied')
                    ON DUPLICATE KEY UPDATE status = VALUES(status)
                    """,
                    (job_id, candidate_id),
                )

        connection.commit()
    finally:
        cursor.close()


def main():
    connection = None
    try:
        config = _base_db_config()
        create_database_if_missing(config)

        connection = mysql.connector.connect(**config)
        schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
        apply_schema(connection, schema_path)
        seed_data(connection)

        print("\n" + "=" * 60)
        print(f"MySQL database '{config['database']}' initialized successfully.")
        print("Schema applied and seed data inserted/updated.")
        print("=" * 60)
    except (Error, ValueError) as exc:
        if connection:
            connection.rollback()
        print(f"\nSetup failed: {exc}")
    finally:
        if connection and connection.is_connected():
            connection.close()
            print("Database connection closed.")


if __name__ == "__main__":
    main()
