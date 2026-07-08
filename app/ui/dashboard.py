import plotly.graph_objects as go
import streamlit as st

from app.models import Insight, ProductIntelligenceReport


def render() -> None:
    report: ProductIntelligenceReport | None = st.session_state.get("report")
    if report is None:
        st.warning("No analysis available yet.")
        if st.button("Start a new analysis"):
            _reset_and_go_home()
        return

    _render_header(report)
    _render_executive_summary(report)
    _render_sentiment(report)

    st.divider()
    _render_insight_section("Top Customer Problems", report.top_problems, report)
    _render_insight_section("Feature Requests", report.feature_requests, report)
    _render_insight_section("Positive Feedback", report.positive_feedback, report)
    _render_insight_section("Critical Issues", report.critical_issues, report)

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Export Report as PDF", type="primary"):
            st.session_state.stage = "report"
            st.rerun()
    with col2:
        if st.button("Start a new analysis"):
            _reset_and_go_home()


def _reset_and_go_home() -> None:
    st.session_state.report = None
    st.session_state.stage = "home"
    st.session_state.app_preview = None
    st.rerun()


def _render_header(report: ProductIntelligenceReport) -> None:
    st.markdown(f"## {report.app_name}")
    cols = st.columns(3)
    cols[0].metric("Platform", report.platform.replace("_", " ").title())
    cols[1].metric("Overall Rating", f"{report.overall_rating:.1f} / 5")
    cols[2].metric("Reviews Analyzed", report.reviews_analyzed)

    if report.failed_batch_count:
        st.info(
            f"{report.failed_batch_count} of {report.total_batch_count} review batches "
            "could not be analyzed and were excluded from this report."
        )


def _render_executive_summary(report: ProductIntelligenceReport) -> None:
    st.markdown("### Executive Summary")
    st.write(report.executive_summary)


def _render_sentiment(report: ProductIntelligenceReport) -> None:
    st.markdown("### Overall Sentiment")
    sentiment = report.overall_sentiment
    fig = go.Figure(
        data=[
            go.Bar(
                x=["Positive", "Neutral", "Negative"],
                y=[
                    sentiment.get("positive_pct", 0),
                    sentiment.get("neutral_pct", 0),
                    sentiment.get("negative_pct", 0),
                ],
                marker_color=["#2E7D32", "#F9A825", "#C62828"],
            )
        ]
    )
    fig.update_layout(
        yaxis_title="Percent of reviews",
        height=300,
        margin=dict(l=20, r=20, t=20, b=20),
    )
    st.plotly_chart(fig, width="stretch")


def _render_insight_section(
    title: str, insights: list[Insight], report: ProductIntelligenceReport
) -> None:
    st.markdown(f"### {title}")
    if not insights:
        st.caption("None identified.")
        return

    for i, insight in enumerate(insights):
        label = f"{insight.title} — mentioned {insight.frequency} time(s)"
        if insight.severity:
            label += f" · severity: {insight.severity}"
        with st.expander(label):
            if not insight.supporting_review_ids:
                st.caption("No supporting reviews available.")
            for rid in insight.supporting_review_ids[:5]:
                review = report.reviews_by_id.get(rid)
                if review:
                    st.markdown(f"> \"{review.text}\" — {review.author} ({review.rating}★)")
            if st.button("View details", key=f"detail_{title}_{i}"):
                st.session_state.selected_insight = insight
                st.session_state.stage = "detail"
                st.rerun()
