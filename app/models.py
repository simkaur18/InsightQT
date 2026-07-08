from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class SourcePlatform(str, Enum):
    GOOGLE_PLAY = "google_play"
    APPLE_APP_STORE = "apple_app_store"


@dataclass(frozen=True)
class RawReview:
    """Exact shape returned by a ReviewSource connector, pre-cleaning."""

    review_id: str
    author: str
    rating: int
    text: str
    date: datetime
    source: SourcePlatform
    app_version: str | None = None
    thumbs_up_count: int = 0


@dataclass
class CleanReview:
    """Post-processing_service shape. This is what ai_service consumes."""

    review_id: str
    author: str
    rating: int
    text: str
    date: datetime
    language: str
    source: SourcePlatform


@dataclass
class Insight:
    """A single theme, problem, feature request, positive highlight, or critical issue."""

    category: str  # "problem" | "feature_request" | "positive" | "critical_issue"
    title: str
    frequency: int
    supporting_review_ids: list[str] = field(default_factory=list)
    severity: str | None = None


@dataclass
class ProductIntelligenceReport:
    app_name: str
    platform: str
    overall_rating: float
    reviews_analyzed: int
    executive_summary: str
    overall_sentiment: dict  # {"positive_pct": float, "neutral_pct": float, "negative_pct": float}
    top_problems: list[Insight]
    feature_requests: list[Insight]
    positive_feedback: list[Insight]
    critical_issues: list[Insight]
    reviews_by_id: dict[str, CleanReview]
    failed_batch_count: int = 0
    total_batch_count: int = 0
