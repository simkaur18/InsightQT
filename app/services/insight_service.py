import logging
from collections.abc import Callable

from app.exceptions import AIAnalysisError
from app.models import CleanReview, Insight, ProductIntelligenceReport
from app.services import ai_service
from app.services.ai_service import AggregatedReport, CriticalTopItem, TopItem

logger = logging.getLogger(__name__)


def _normalize_sentiment_pcts(sentiment: dict) -> dict:
    """Defensively rescale sentiment percentages to a 0-100 scale.

    The model is instructed to return 0-100 values, but smaller open models
    don't always follow that instruction — if it returns 0-1 fractions
    instead (values summing to ~1 rather than ~100), rescale so the
    dashboard/PDF don't silently render "0%" for everything.
    """
    total = sum(sentiment.values())
    if 0 < total <= 1.5:
        return {k: v * 100 for k, v in sentiment.items()}
    return sentiment


def _to_insight(
    item: TopItem | CriticalTopItem,
    category: str,
    valid_review_ids: set[str],
) -> Insight:
    review_ids = [rid for rid in item.representative_review_ids if rid in valid_review_ids]
    dropped = len(item.representative_review_ids) - len(review_ids)
    if dropped:
        logger.warning(
            "Dropped %d hallucinated review_id(s) from insight '%s'", dropped, item.title
        )
    severity = getattr(item, "severity", None)
    return Insight(
        category=category,
        title=item.title,
        frequency=item.frequency if isinstance(item, TopItem) else len(review_ids),
        supporting_review_ids=review_ids,
        severity=severity,
    )


def _build_report_from_aggregation(
    aggregated: AggregatedReport,
    reviews_by_id: dict[str, CleanReview],
    app_name: str,
    platform: str,
    overall_rating: float,
    total_batches: int,
    failed_batches: int,
) -> ProductIntelligenceReport:
    valid_ids = set(reviews_by_id.keys())
    return ProductIntelligenceReport(
        app_name=app_name,
        platform=platform,
        overall_rating=overall_rating,
        reviews_analyzed=len(reviews_by_id),
        executive_summary=aggregated.executive_summary,
        overall_sentiment=_normalize_sentiment_pcts(aggregated.overall_sentiment.model_dump()),
        top_problems=[_to_insight(i, "problem", valid_ids) for i in aggregated.top_problems],
        feature_requests=[
            _to_insight(i, "feature_request", valid_ids) for i in aggregated.feature_requests
        ],
        positive_feedback=[
            _to_insight(i, "positive", valid_ids) for i in aggregated.positive_feedback
        ],
        critical_issues=[
            _to_insight(i, "critical_issue", valid_ids) for i in aggregated.critical_issues
        ],
        reviews_by_id=reviews_by_id,
        failed_batch_count=failed_batches,
        total_batch_count=total_batches,
    )


def build_report(
    clean_reviews: list[CleanReview],
    app_name: str,
    platform: str,
    overall_rating: float,
    progress_callback: Callable[[int, int], None] | None = None,
) -> ProductIntelligenceReport:
    """Run the full AI analysis pipeline and assemble a ProductIntelligenceReport."""
    reviews_by_id = {r.review_id: r for r in clean_reviews}

    batch_extractions, total_batches, failed_batches = ai_service.analyze_reviews_in_batches(
        clean_reviews, progress_callback=progress_callback
    )

    if not batch_extractions:
        raise AIAnalysisError(
            "AI analysis failed for all review batches. Please retry — if this "
            "keeps happening, check your GROQ_API_KEY and network connection."
        )

    aggregated = ai_service.aggregate_batches(batch_extractions)

    return _build_report_from_aggregation(
        aggregated,
        reviews_by_id,
        app_name,
        platform,
        overall_rating,
        total_batches,
        failed_batches,
    )
