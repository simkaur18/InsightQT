import os

import psycopg2
import psycopg2.extras

from app.exceptions import MissingDatabaseURLError


def get_connection() -> psycopg2.extensions.connection:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise MissingDatabaseURLError(
            "DATABASE_URL is not configured. Add it to your .env file."
        )
    return psycopg2.connect(database_url, cursor_factory=psycopg2.extras.RealDictCursor)


def init_db() -> None:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    is_admin BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TEXT NOT NULL
                )
                """
            )
        conn.commit()
    finally:
        conn.close()
