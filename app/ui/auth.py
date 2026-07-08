import streamlit as st

from app.exceptions import InvalidCredentialsError
from app.services import user_service


def is_authenticated() -> bool:
    return bool(st.session_state.get("logged_in"))


def _log_in(email: str, is_admin: bool) -> None:
    st.session_state.logged_in = True
    st.session_state.user_email = email
    st.session_state.is_admin = is_admin


def render_bootstrap() -> None:
    st.markdown("## Welcome to InsightQT")
    st.info("No users are configured yet. Create the first account — it will be an admin.")

    with st.form("bootstrap_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm password", type="password")
        submitted = st.form_submit_button("Create admin account", type="primary")

    if not submitted:
        return

    if not email or "@" not in email:
        st.error("Enter a valid email address.")
        return
    if len(password) < 8:
        st.error("Password must be at least 8 characters.")
        return
    if password != confirm_password:
        st.error("Passwords don't match.")
        return

    user_service.create_user(email, password, is_admin=True)
    _log_in(email.strip().lower(), is_admin=True)
    st.rerun()


def render_login() -> None:
    st.markdown("## Log in to InsightQT")

    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in", type="primary")

    if not submitted:
        return

    try:
        user = user_service.verify_credentials(email, password)
    except InvalidCredentialsError as exc:
        st.error(str(exc))
        return

    _log_in(user["email"], user["is_admin"])
    st.rerun()


def log_out() -> None:
    st.session_state.logged_in = False
    st.session_state.user_email = None
    st.session_state.is_admin = False
