import pytest

import app.db as db_module
from app.exceptions import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from app.services import user_service

TEST_DATABASE_URL = "postgresql://insightqt_test:testpass123@localhost:5432/insightqt_test"


@pytest.fixture(autouse=True)
def isolated_db(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", TEST_DATABASE_URL)
    conn = db_module.get_connection()
    with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS users")
    conn.commit()
    conn.close()
    db_module.init_db()


def test_any_users_exist_false_initially():
    assert user_service.any_users_exist() is False


def test_create_user_makes_any_users_exist_true():
    user_service.create_user("admin@example.com", "password123", is_admin=True)
    assert user_service.any_users_exist() is True


def test_create_user_duplicate_email_raises():
    user_service.create_user("admin@example.com", "password123")
    with pytest.raises(UserAlreadyExistsError):
        user_service.create_user("admin@example.com", "otherpassword")


def test_create_user_email_is_case_normalized():
    user_service.create_user("Admin@Example.com", "password123")
    with pytest.raises(UserAlreadyExistsError):
        user_service.create_user("admin@example.com", "otherpassword")


def test_verify_credentials_correct_password_returns_user():
    user_service.create_user("admin@example.com", "password123", is_admin=True)
    user = user_service.verify_credentials("admin@example.com", "password123")
    assert user == {"email": "admin@example.com", "is_admin": True}


def test_verify_credentials_wrong_password_raises():
    user_service.create_user("admin@example.com", "password123")
    with pytest.raises(InvalidCredentialsError):
        user_service.verify_credentials("admin@example.com", "wrongpassword")


def test_verify_credentials_unknown_email_raises():
    with pytest.raises(InvalidCredentialsError):
        user_service.verify_credentials("nobody@example.com", "password123")


def test_list_users_returns_all_users_ordered_by_creation():
    user_service.create_user("first@example.com", "password123")
    user_service.create_user("second@example.com", "password123", is_admin=True)
    users = user_service.list_users()
    assert [u["email"] for u in users] == ["first@example.com", "second@example.com"]
    assert users[1]["is_admin"] is True


def test_remove_user_deletes_them():
    user_service.create_user("admin@example.com", "password123")
    user_service.remove_user("admin@example.com")
    assert user_service.any_users_exist() is False


def test_remove_user_unknown_email_raises():
    with pytest.raises(UserNotFoundError):
        user_service.remove_user("nobody@example.com")


def test_set_admin_updates_flag():
    user_service.create_user("member@example.com", "password123", is_admin=False)
    user_service.set_admin("member@example.com", True)
    users = user_service.list_users()
    assert users[0]["is_admin"] is True


def test_set_admin_unknown_email_raises():
    with pytest.raises(UserNotFoundError):
        user_service.set_admin("nobody@example.com", True)
