from datetime import datetime

from app.models import CleanReview, Insight, ProductIntelligenceReport, RawReview, SourcePlatform


def test_raw_review_construction_and_review_id_survives():
    review = RawReview(
        review_id="abc123",
        author="Jane",
        rating=5,
        text="Great app!",
        date=datetime(2026, 1, 1),
        source=SourcePlatform.GOOGLE_PLAY,
    )
    clean = CleanReview(
        review_id=review.review_id,
        author=review.author,
        rating=review.rating,
        text=review.text,
        date=review.date,
        language="en",
        source=review.source,
    )
    assert clean.review_id == "abc123"


def test_raw_review_is_frozen():
    review = RawReview(
        review_id="abc",
        author="A",
        rating=1,
        text="x",
        date=datetime.now(),
        source=SourcePlatform.GOOGLE_PLAY,
    )
    try:
        review.rating = 5
        assert False, "expected FrozenInstanceError"
    except Exception:
        pass


def test_insight_defaults():
    insight = Insight(category="problem", title="Crashes on launch", frequency=10)
    assert insight.supporting_review_ids == []
    assert insight.severity is None


def test_product_intelligence_report_construction():
    report = ProductIntelligenceReport(
        app_name="Example App",
        platform="google_play",
        overall_rating=4.2,
        reviews_analyzed=100,
        executive_summary="Overall positive.",
        overall_sentiment={"positive_pct": 70.0, "neutral_pct": 20.0, "negative_pct": 10.0},
        top_problems=[],
        feature_requests=[],
        positive_feedback=[],
        critical_issues=[],
        reviews_by_id={},
    )
    assert report.reviews_analyzed == 100
    assert report.failed_batch_count == 0
