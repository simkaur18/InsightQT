import streamlit as st

from app.exceptions import InsightQTError
from app.services import user_service


def render() -> None:
    st.markdown("## Admin: Manage Authorized Users")

    if st.session_state.get("error_message"):
        st.error(st.session_state.error_message)
        st.session_state.error_message = None
    if st.session_state.get("success_message"):
        st.success(st.session_state.success_message)
        st.session_state.success_message = None

    users = user_service.list_users()

    st.markdown("### Current users")
    st.dataframe(
        [{"Email": u["email"], "Admin": u["is_admin"], "Added": u["created_at"]} for u in users],
        width="stretch",
        hide_index=True,
    )
    admin_count = sum(1 for u in users if u["is_admin"])

    st.markdown("### Add a new user")
    with st.form("add_user_form", clear_on_submit=True):
        email = st.text_input("Email")
        password = st.text_input("Temporary password", type="password")
        is_admin = st.checkbox("Grant admin access")
        submitted_add = st.form_submit_button("Add user", type="primary")

    if submitted_add:
        if not email or "@" not in email:
            st.session_state.error_message = "Enter a valid email address."
        elif len(password) < 8:
            st.session_state.error_message = "Password must be at least 8 characters."
        else:
            try:
                user_service.create_user(email, password, is_admin=is_admin)
                st.session_state.success_message = f"Added {email}."
            except InsightQTError as exc:
                st.session_state.error_message = str(exc)
        st.rerun()

    st.markdown("### Remove a user")
    emails = [u["email"] for u in users]
    if emails:
        with st.form("remove_user_form"):
            target = st.selectbox("User to remove", options=emails)
            submitted_remove = st.form_submit_button("Remove user")

        if submitted_remove:
            target_is_admin = next(u["is_admin"] for u in users if u["email"] == target)
            if target_is_admin and admin_count <= 1:
                st.session_state.error_message = (
                    "Can't remove the only remaining admin. Grant admin to someone else first."
                )
            else:
                try:
                    user_service.remove_user(target)
                    st.session_state.success_message = f"Removed {target}."
                except InsightQTError as exc:
                    st.session_state.error_message = str(exc)
            st.rerun()
    else:
        st.caption("No users to remove.")
