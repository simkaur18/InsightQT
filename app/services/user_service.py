from datetime import datetime

import bcrypt
import psycopg2

from app.db import get_connection
from app.exceptions import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
    UserNotFoundError,
)


def any_users_exist() -> bool:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM users LIMIT 1")
            return cur.fetchone() is not None
    finally:
        conn.close()


def create_user(email: str, password: str, is_admin: bool = False) -> None:
    email = email.strip().lower()
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    conn = get_connection()
    try:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO users (email, password_hash, is_admin, created_at) "
                    "VALUES (%s, %s, %s, %s)",
                    (email, password_hash, is_admin, datetime.now().isoformat()),
                )
            conn.commit()
        except psycopg2.errors.UniqueViolation as exc:
            conn.rollback()
            raise UserAlreadyExistsError(f"A user with email {email} already exists.") from exc
    finally:
        conn.close()


def verify_credentials(email: str, password: str) -> dict:
    email = email.strip().lower()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE email = %s", (email,))
            row = cur.fetchone()
    finally:
        conn.close()

    if row is None:
        raise InvalidCredentialsError("Incorrect email or password.")
    if not bcrypt.checkpw(password.encode("utf-8"), row["password_hash"].encode("utf-8")):
        raise InvalidCredentialsError("Incorrect email or password.")

    return {"email": row["email"], "is_admin": bool(row["is_admin"])}


def list_users() -> list[dict]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT email, is_admin, created_at FROM users ORDER BY created_at")
            rows = cur.fetchall()
    finally:
        conn.close()
    return [
        {"email": row["email"], "is_admin": bool(row["is_admin"]), "created_at": row["created_at"]}
        for row in rows
    ]


def remove_user(email: str) -> None:
    email = email.strip().lower()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE email = %s", (email,))
            deleted = cur.rowcount
        conn.commit()
        if deleted == 0:
            raise UserNotFoundError(f"No user found with email {email}.")
    finally:
        conn.close()


def set_admin(email: str, is_admin: bool) -> None:
    email = email.strip().lower()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET is_admin = %s WHERE email = %s", (is_admin, email)
            )
            updated = cur.rowcount
        conn.commit()
        if updated == 0:
            raise UserNotFoundError(f"No user found with email {email}.")
    finally:
        conn.close()
