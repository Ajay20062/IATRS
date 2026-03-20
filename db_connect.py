from ats_api.db import Error, create_db_connection


def get_db_connection():
    """
    Backward-compatible wrapper used by existing setup scripts.

    Returns:
        mysql.connector.connection.MySQLConnection | None
    """
    try:
        return create_db_connection()
    except (Error, ValueError) as exc:
        print(f"Error: Could not connect to MySQL Server - {exc}")
        return None
