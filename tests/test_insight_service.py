from datetime import datetime
from unittest.mock import MagicMock

import pytest

from app.exceptions import AIAnalysisError
from app.models import CleanReview, SourcePlatform
from app.services import insight_service
from app.services.ai_service import (
    AggregatedReport,
    CriticalTopItem,
    OverallSentiment,
    TopItem,
)
from app.services.insight_service import _normalize_sentiment_pcts


def test_normalize_sentiment_pcts_rescales_fractions():
    result = _normalize_sentiment_pcts(
        {"positive_pct": 0.5, "neutral_pct": 0.3, "negative_pct": 0.2}
    )
    assert result == {"positive_pct": 50.0, "neutral_pct": 30.0, "negative_pct": 20.0}


def test_normalize_sentiment_pcts_leaves_already_scaled_values_alone():
    result = _normalize_sentiment_pcts(
        {"positive_pct": 70.0, "neutral_pct": 20.0, "negative_pct": 10.0}
    )
    assert result == {"positive_pct": 70.0, "neutral_pct": 20.0, "negative_pct": 10.0}


def _clean_review(review_id: str) -> CleanReview:
    return CleanReview(
        review_id=review_id,
        author="Author",
        rating=4,
        text="Solid app.",
        date=datetime(2026, 1, 1),
        language="en",
        source=SourcePlatform.GOOGLE_PLAY,
    )


def _aggregated_report(feature_review_ids, critical_review_ids) -> AggregatedReport:
    return AggregatedReport(
        executive_summary="Solid app overall.",
        overall_sentiment=OverallSentiment(positive_pct=70.0, neutral_pct=20.0, negative_pct=10.0),
        top_problems=[],
        feature_requests=[
            TopItem(title="Add widgets", frequency=2, representative_review_ids=feature_review_ids)
        ],
        positive_feedback=[],
        critical_issues=[
            CriticalTopItem(
                title="Crashes",
                severity="high",
                representative_review_ids=critical_review_ids,
            )
        ],
    )


def test_build_report_raises_when_all_batches_fail(mocker):
    reviews = [_clean_review("1"), _clean_review("2")]
    mocker.patch.object(
        insight_service.ai_service,
        "analyze_reviews_in_batches",
        return_value=([], 2, 2),
    )
    with pytest.raises(AIAnalysisError):
        insight_service.build_report(reviews, "Example App", "google_play", 4.0)


def test_build_report_filters_hallucinated_review_ids(mocker):
    reviews = [_clean_review("1"), _clean_review("2")]
    mocker.patch.object(
        insight_service.ai_service,
        "analyze_reviews_in_batches",
        return_value=(["fake-batch-result"], 1, 0),
    )
    mocker.patch.object(
        insight_service.ai_service,
        "aggregate_batches",
        return_value=_aggregated_report(
            feature_review_ids=["1", "does-not-exist"],
            critical_review_ids=["2"],
        ),
    )

    report = insight_service.build_report(reviews, "Example App", "google_play", 4.0)

    assert report.reviews_analyzed == 2
    assert report.feature_requests[0].supporting_review_ids == ["1"]
    assert report.critical_issues[0].supporting_review_ids == ["2"]
    assert report.critical_issues[0].severity == "high"


def test_build_report_passes_through_progress_callback(mocker):
    reviews = [_clean_review("1")]
    captured = {}

    def fake_analyze(reviews_arg, progress_callback=None):
        captured["callback"] = progress_callback
        if progress_callback:
            progress_callback(1, 1)
        return (["fake-batch-result"], 1, 0)

    mocker.patch.object(
        insight_service.ai_service, "analyze_reviews_in_batches", side_effect=fake_analyze
    )
    mocker.patch.object(
        insight_service.ai_service,
        "aggregate_batches",
        return_value=_aggregated_report(["1"], []),
    )

    seen = []
    insight_service.build_report(
        reviews, "Example App", "google_play", 4.0, progress_callback=lambda d, t: seen.append((d, t))
    )
    assert seen == [(1, 1)]
