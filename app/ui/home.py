import streamlit as st

from app.exceptions import InsightQTError
from app.services import insight_service, processing_service
from app.services.integration_service import GooglePlayReviewSource
from app.utils import validators
from app.utils.constants import (
    DATE_RANGE_PRESETS,
    DEFAULT_DATE_RANGE_PRESET,
    MAX_REVIEWS_TO_ANALYZE,
)
from app.utils.helpers import resolve_date_range_since


def render() -> None:
    stage = st.session_state.stage
    if stage == "home":
        _render_landing()
    elif stage == "preview":
        _render_preview()
    elif stage == "analyzing":
        _run_analysis()


def _render_landing() -> None:
    st.markdown("## Analyze App Reviews with AI")
    st.write(
        "Paste your app's Google Play Store URL and generate actionable "
        "product insights in minutes."
    )

    if st.session_state.get("error_message"):
        st.error(st.session_state.error_message)

    url = st.text_input(
        "App URL",
        placeholder="Paste Google Play Store URL",
        key="url_input",
        label_visibility="collapsed",
    )
    st.caption("Supported platform: Google Play Store. (Apple App Store support is coming soon.)")

    if st.button("Look Up App", type="primary"):
        st.session_state.error_message = None
        try:
            platform, app_id = validators.validate_and_extract_app_id(url)
            metadata = GooglePlayReviewSource().get_app_metadata(app_id)
        except InsightQTError as exc:
            st.session_state.error_message = str(exc)
            st.rerun()
            return
        except Exception as exc:  # noqa: BLE001 - top-level guard, never crash the app
            st.session_state.error_message = f"Unexpected error: {exc}"
            st.rerun()
            return

        st.session_state.app_preview = {"platform": platform, "app_id": app_id, **metadata}
        st.session_state.stage = "preview"
        st.rerun()


def _render_preview() -> None:
    preview = st.session_state.get("app_preview")
    if not preview:
        st.session_state.stage = "home"
        st.rerun()
        return

    st.markdown(f"## {preview['title']}")
    cols = st.columns(2)
    cols[0].metric("Rating", f"{preview['score']:.1f} / 5")
    cols[1].metric("Total Reviews on Play Store", f"{preview['total_reviews']:,}")

    if st.session_state.get("error_message"):
        st.error(st.session_state.error_message)

    st.markdown("### Choose a date range to analyze")
    preset_labels = list(DATE_RANGE_PRESETS.keys())
    date_range_choice = st.selectbox(
        "Date range",
        options=preset_labels,
        index=preset_labels.index(DEFAULT_DATE_RANGE_PRESET),
        key="date_range_choice",
        label_visibility="collapsed",
    )
    if DATE_RANGE_PRESETS[date_range_choice] is None:
        st.caption(
            f"If this app has more than {MAX_REVIEWS_TO_ANALYZE} reviews, only the "
            f"most recent {MAX_REVIEWS_TO_ANALYZE} are analyzed. Otherwise, every "
            "review is analyzed."
        )
    else:
        st.caption(
            f"If this app has more than {MAX_REVIEWS_TO_ANALYZE} reviews in your "
            f"selected range, only the most recent {MAX_REVIEWS_TO_ANALYZE} are "
            "analyzed. Otherwise, every review in range is analyzed."
        )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Choose a different app"):
            st.session_state.stage = "home"
            st.session_state.app_preview = None
            st.rerun()
    with col2:
        if st.button("Analyze Reviews", type="primary"):
            st.session_state.error_message = None
            st.session_state.stage = "analyzing"
            st.rerun()


def _run_analysis() -> None:
    preview = st.session_state.get("app_preview")
    if not preview:
        st.session_state.stage = "home"
        st.rerun()
        return

    app_id = preview["app_id"]
    platform = preview["platform"]
    date_range_choice = st.session_state.get("date_range_choice", DEFAULT_DATE_RANGE_PRESET)
    since = resolve_date_range_since(date_range_choice)

    with st.status("Analyzing app reviews...", expanded=True) as status:
        try:
            st.write(f"Retrieving reviews ({date_range_choice})...")
            raw_reviews, hit_cap = GooglePlayReviewSource().fetch_reviews(
                app_id, MAX_REVIEWS_TO_ANALYZE, since=since
            )

            if not raw_reviews:
                status.update(label="No reviews found", state="error")
                st.session_state.error_message = (
                    f"No reviews found for {preview['title']} in the selected date "
                    f"range ({date_range_choice}). Try a wider range."
                )
                st.session_state.stage = "preview"
                st.rerun()
                return

            if hit_cap:
                st.write(
                    f"Retrieved {len(raw_reviews)} reviews — this app has more than "
                    f"{MAX_REVIEWS_TO_ANALYZE} reviews in the selected range, so these "
                    "are the most recent ones. Cleaning & processing..."
                )
            else:
                st.write(
                    f"Retrieved all {len(raw_reviews)} reviews in this range. "
                    "Cleaning & processing..."
                )
            clean_reviews = processing_service.clean_reviews(raw_reviews)

            st.write("Running AI sentiment analysis and detecting themes...")
            progress_placeholder = st.empty()

            def _on_batch_progress(done: int, total: int) -> None:
                progress_placeholder.write(f"Analyzed batch {done}/{total}...")

            st.write("Generating product insights...")
            report = insight_service.build_report(
                clean_reviews,
                app_name=preview["title"],
                platform=platform.value,
                overall_rating=preview["score"],
                progress_callback=_on_batch_progress,
            )

            status.update(label="Analysis complete", state="complete")
        except InsightQTError as exc:
            status.update(label="Analysis failed", state="error")
            st.session_state.error_message = str(exc)
            st.session_state.stage = "preview"
            st.rerun()
            return
        except Exception as exc:  # noqa: BLE001 - top-level guard, never crash the app
            status.update(label="Analysis failed", state="error")
            st.session_state.error_message = f"Unexpected error: {exc}"
            st.session_state.stage = "preview"
            st.rerun()
            return

    st.session_state.report = report
    st.session_state.stage = "dashboard"
    st.rerun()
