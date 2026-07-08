import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv()

import streamlit as st

from app.db import init_db
from app.services import user_service
from app.ui import admin, auth, dashboard, home, insight_detail, report, settings

st.set_page_config(page_title="InsightQT", page_icon="📊", layout="wide")

_DEFAULTS = {
    "stage": "home",
    "app_preview": None,
    "report": None,
    "selected_insight": None,
    "error_message": None,
    "pdf_bytes": None,
    "logged_in": False,
    "user_email": None,
    "is_admin": False,
}
for key, default in _DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = default

init_db()

if not user_service.any_users_exist():
    auth.render_bootstrap()
    st.stop()

if not auth.is_authenticated():
    auth.render_login()
    st.stop()

with st.sidebar:
    st.markdown("# InsightQT")
    st.caption("AI-powered Product Intelligence")
    st.divider()
    if st.button("🏠 Home / New Analysis", width="stretch"):
        st.session_state.stage = "home"
        st.session_state.report = None
        st.session_state.app_preview = None
        st.session_state.pdf_bytes = None
        st.rerun()
    if st.button("⚙️ Settings", width="stretch"):
        st.session_state.stage = "settings"
        st.rerun()
    if st.session_state.is_admin and st.button("🔑 Admin", width="stretch"):
        st.session_state.stage = "admin"
        st.rerun()
    st.divider()
    st.caption(f"Logged in as {st.session_state.user_email}")
    if st.button("Log out", width="stretch"):
        auth.log_out()
        st.session_state.stage = "home"
        st.rerun()

stage = st.session_state.stage

if stage in ("home", "preview", "analyzing"):
    home.render()
elif stage == "dashboard":
    dashboard.render()
elif stage == "detail":
    insight_detail.render()
elif stage == "report":
    report.render()
elif stage == "settings":
    settings.render()
elif stage == "admin":
    admin.render()
else:
    st.session_state.stage = "home"
    st.rerun()
