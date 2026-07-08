from datetime import datetime
from io import BytesIO

from pypdf import PdfReader

from app.models import CleanReview, Insight, ProductIntelligenceReport, SourcePlatform
from app.services.report_service import generate_pdf


def _sample_report() -> ProductIntelligenceReport:
    review = CleanReview(
        review_id="1",
        author="Jane",
        rating=5,
        text="Fantastic app, works flawlessly.",
        date=datetime(2026, 1, 1),
        language="en",
        source=SourcePlatform.GOOGLE_PLAY,
    )
    return ProductIntelligenceReport(
        app_name="Example App",
        platform="google_play",
        overall_rating=4.5,
        reviews_analyzed=1,
        executive_summary="Users are overwhelmingly satisfied.",
        overall_sentiment={"positive_pct": 90.0, "neutral_pct": 8.0, "negative_pct": 2.0},
        top_problems=[
            Insight(category="problem", title="Occasional lag", frequency=3, supporting_review_ids=["1"])
        ],
        feature_requests=[],
        positive_feedback=[
            Insight(category="positive", title="Great UX", frequency=5, supporting_review_ids=["1"])
        ],
        critical_issues=[],
        reviews_by_id={"1": review},
    )


def test_generate_pdf_produces_nonempty_valid_pdf():
    pdf_bytes = generate_pdf(_sample_report())
    assert len(pdf_bytes) > 0
    reader = PdfReader(BytesIO(pdf_bytes))
    assert len(reader.pages) >= 1


def test_generate_pdf_handles_empty_insight_lists():
    report = _sample_report()
    report.top_problems = []
    report.positive_feedback = []
    pdf_bytes = generate_pdf(report)
    assert len(pdf_bytes) > 0
