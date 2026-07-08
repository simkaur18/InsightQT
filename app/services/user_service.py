import sqlite3
from datetime import datetime

import bcrypt

from app.db import get_connection
from app.exceptions import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
    UserNotFoundError,
)


def any_users_exist() -> bool:
    conn = get_connection()
    try:
        row = conn.execute("SELECT 1 FROM users LIMIT 1").fetchone()
        return row is not None
    finally:
        conn.close()


def create_user(email: str, password: str, is_admin: bool = False) -> None:
    email = email.strip().lower()
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    conn = get_connection()
    try:
        try:
            conn.execute(
                "INSERT INTO users (email, password_hash, is_admin, created_at) "
                "VALUES (?, ?, ?, ?)",
                (email, password_hash, int(is_admin), datetime.now().isoformat()),
            )
            conn.commit()
        except sqlite3.IntegrityError as exc:
            raise UserAlreadyExistsError(f"A user with email {email} already exists.") from exc
    finally:
        conn.close()


def verify_credentials(email: str, password: str) -> dict:
    email = email.strip().lower()
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
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
        rows = conn.execute(
            "SELECT email, is_admin, created_at FROM users ORDER BY created_at"
        ).fetchall()
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
        cursor = conn.execute("DELETE FROM users WHERE email = ?", (email,))
        conn.commit()
        if cursor.rowcount == 0:
            raise UserNotFoundError(f"No user found with email {email}.")
    finally:
        conn.close()


def set_admin(email: str, is_admin: bool) -> None:
    email = email.strip().lower()
    conn = get_connection()
    try:
        cursor = conn.execute(
            "UPDATE users SET is_admin = ? WHERE email = ?", (int(is_admin), email)
        )
        conn.commit()
        if cursor.rowcount == 0:
            raise UserNotFoundError(f"No user found with email {email}.")
    finally:
        conn.close()
