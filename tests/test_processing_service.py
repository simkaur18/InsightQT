from datetime import datetime

from app.models import RawReview, SourcePlatform
from app.services.processing_service import clean_reviews


def _raw(review_id, text, rating=5):
    return RawReview(
        review_id=review_id,
        author="Author",
        rating=rating,
        text=text,
        date=datetime(2026, 1, 1),
        source=SourcePlatform.GOOGLE_PLAY,
    )


def test_clean_reviews_empty_input():
    assert clean_reviews([]) == []


def test_clean_reviews_dedupes_by_review_id():
    raws = [_raw("1", "Great app"), _raw("1", "Great app duplicate id")]
    cleaned = clean_reviews(raws)
    assert len(cleaned) == 1
    assert cleaned[0].review_id == "1"


def test_clean_reviews_dedupes_by_text():
    raws = [_raw("1", "Same review text"), _raw("2", "Same review text")]
    cleaned = clean_reviews(raws)
    assert len(cleaned) == 1


def test_clean_reviews_normalizes_whitespace():
    raws = [_raw("1", "Line one\n\n  Line   two  ")]
    cleaned = clean_reviews(raws)
    assert cleaned[0].text == "Line one Line two"


def test_clean_reviews_detects_language():
    raws = [_raw("1", "This application works extremely well for everyday tasks")]
    cleaned = clean_reviews(raws)
    assert cleaned[0].language == "en"


def test_clean_reviews_handles_empty_text_without_raising():
    raws = [_raw("1", "")]
    cleaned = clean_reviews(raws)
    assert cleaned[0].language == "unknown"
