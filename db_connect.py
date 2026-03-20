"""
Legacy compatibility module for scripts that import get_db_connection().
"""

import os
from urllib.parse import urlparse

import pymysql


def _read_mysql_config_from_database_url():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return {
            "host": os.getenv("DB_HOST", "localhost"),
            "user": os.getenv("DB_USER", "root"),
            "password": os.getenv("DB_PASSWORD", ""),
            "database": os.getenv("DB_NAME", "iatrs"),
            "port": int(os.getenv("DB_PORT", "3306")),
        }

    # Expected format: mysql+pymysql://user:password@host:port/db
    parsed = urlparse(database_url.replace("mysql+pymysql", "mysql", 1))
    return {
        "host": parsed.hostname or "localhost",
        "user": parsed.username or "root",
        "password": parsed.password or "",
        "database": (parsed.path or "/iatrs").lstrip("/"),
        "port": int(parsed.port or 3306),
    }


def get_db_connection():
    config = _read_mysql_config_from_database_url()
    return pymysql.connect(
        host=config["host"],
        user=config["user"],
        password=config["password"],
        database=config["database"],
        port=config["port"],
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )
