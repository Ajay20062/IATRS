import os

from dotenv import load_dotenv

load_dotenv()


def _as_bool(value: str, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_int(value: str, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def load_app_config() -> dict:
    return {
        "DEBUG": _as_bool(os.getenv("FLASK_DEBUG"), False),
        "HOST": os.getenv("HOST", "127.0.0.1"),
        "PORT": _as_int(os.getenv("PORT"), 5000),
    }


def load_db_config() -> dict:
    return {
        "host": os.getenv("DB_HOST"),
        "port": _as_int(os.getenv("DB_PORT"), 3306),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "database": os.getenv("DB_NAME"),
    }
