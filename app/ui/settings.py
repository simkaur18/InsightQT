import os

import streamlit as st

from app.utils.constants import MAX_REVIEWS_TO_ANALYZE


def render() -> None:
    st.markdown("## Settings")

    st.markdown("### AI Configuration")
    api_key = os.getenv("GROQ_API_KEY")
    if api_key:
        masked = f"{api_key[:6]}...{api_key[-4:]}" if len(api_key) > 10 else "****"
        st.success(f"GROQ_API_KEY is configured ({masked})")
    else:
        st.error(
            "GROQ_API_KEY is not set. Add it to your .env file "
            "(GROQ_API_KEY=gsk_...) and restart the app to enable AI analysis."
        )
    st.caption(
        "AI analysis runs on Groq's free tier, which has a small per-minute token budget. "
        "Analyses run batch-by-batch with a short pause between calls, so larger review "
        "counts will take noticeably longer than on a paid provider."
    )

    st.markdown("### Analysis Settings")
    st.write(
        "Review scope is chosen per-analysis on the app lookup screen via the date-range "
        "picker (Last 1/3/7 days, 30 days, or All time)."
    )
    st.caption(
        f"Only the most recent {MAX_REVIEWS_TO_ANALYZE} reviews (in your selected range, "
        "or overall for \"All time\") are analyzed, even if the app has many more."
    )
