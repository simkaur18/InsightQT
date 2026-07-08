import streamlit as st

from app.models import Insight, ProductIntelligenceReport


def render() -> None:
    insight: Insight | None = st.session_state.get("selected_insight")
    report: ProductIntelligenceReport | None = st.session_state.get("report")

    if insight is None or report is None:
        st.warning("No insight selected.")
        if st.button("Back to dashboard"):
            st.session_state.stage = "dashboard"
            st.rerun()
        return

    if st.button("← Back to dashboard"):
        st.session_state.stage = "dashboard"
        st.rerun()

    st.markdown(f"## {insight.title}")
    st.caption(f"Category: {insight.category.replace('_', ' ').title()}")

    cols = st.columns(2)
    cols[0].metric("Mentions", insight.frequency)
    if insight.severity:
        cols[1].metric("Severity", insight.severity.title())

    st.markdown("### Supporting Customer Reviews")
    if not insight.supporting_review_ids:
        st.caption("No supporting reviews available for this insight.")
        return

    for rid in insight.supporting_review_ids:
        review = report.reviews_by_id.get(rid)
        if review is None:
            continue
        with st.container(border=True):
            st.markdown(f"**{review.author}** — {review.rating}★ ({review.date:%Y-%m-%d})")
            st.write(review.text)
