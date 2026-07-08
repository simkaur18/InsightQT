import streamlit as st

from app.models import ProductIntelligenceReport
from app.services import report_service


def render() -> None:
    report: ProductIntelligenceReport | None = st.session_state.get("report")
    if report is None:
        st.warning("No analysis available yet.")
        if st.button("Back to dashboard"):
            st.session_state.stage = "dashboard"
            st.rerun()
        return

    if st.button("← Back to dashboard"):
        st.session_state.stage = "dashboard"
        st.rerun()

    st.markdown("## Export Report")
    st.write(f"**{report.app_name}** — Product Intelligence Report")

    st.markdown("#### Included Sections")
    st.write(
        "- Executive Summary\n"
        "- Overall Sentiment\n"
        "- Top Customer Problems\n"
        "- Feature Requests\n"
        "- Positive Feedback\n"
        "- Critical Issues"
    )

    if st.button("Generate PDF", type="primary"):
        with st.spinner("Generating PDF..."):
            pdf_bytes = report_service.generate_pdf(report)
        st.session_state.pdf_bytes = pdf_bytes
        st.success("PDF ready.")

    pdf_bytes = st.session_state.get("pdf_bytes")
    if pdf_bytes:
        file_name = f"{report.app_name.replace(' ', '_')}_insightqt_report.pdf"
        st.download_button(
            "Download PDF",
            data=pdf_bytes,
            file_name=file_name,
            mime="application/pdf",
        )

    st.divider()
    if st.button("Start a new analysis"):
        st.session_state.report = None
        st.session_state.pdf_bytes = None
        st.session_state.stage = "home"
        st.session_state.app_preview = None
        st.rerun()
