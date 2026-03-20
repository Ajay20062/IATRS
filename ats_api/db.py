import mysql.connector
from mysql.connector import Error

from .config import load_db_config


def create_db_connection():
    db_config = load_db_config()
    env_by_field = {
        "host": "localhost",
        "user": "root",
        "database": "ats_db",
    }
    missing = [env_by_field[name] for name in env_by_field if not db_config.get(name)]
    if missing:
        missing_text = ", ".join(missing)
        raise ValueError(f"Missing database environment variables: {missing_text}")

    return mysql.connector.connect(**db_config)


def safe_close(connection=None, cursor=None):
    if cursor:
        cursor.close()
    if connection and connection.is_connected():
        connection.close()


__all__ = ["create_db_connection", "safe_close", "Error"]
