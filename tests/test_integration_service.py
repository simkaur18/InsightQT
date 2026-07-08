from datetime import datetime

import pytest
from google_play_scraper.exceptions import NotFoundError

from app.exceptions import AppNotFoundError, ReviewRetrievalError
from app.services.integration_service import GooglePlayReviewSource


def _fake_review(review_id: str, at: datetime = datetime(2026, 1, 1)):
    return {
        "reviewId": review_id,
        "userName": "Tester",
        "score": 4,
        "content": "It works well.",
        "at": at,
        "reviewCreatedVersion": "1.0.0",
        "thumbsUpCount": 2,
    }


def test_validate_app_exists_true(mocker):
    mocker.patch("app.services.integration_service.google_play_scraper.app", return_value={})
    source = GooglePlayReviewSource()
    assert source.validate_app_exists("com.example.app") is True


def test_validate_app_exists_false(mocker):
    mocker.patch(
        "app.services.integration_service.google_play_scraper.app",
        side_effect=NotFoundError(),
    )
    source = GooglePlayReviewSource()
    assert source.validate_app_exists("com.nonexistent.app") is False


def test_get_app_metadata_raises_app_not_found(mocker):
    mocker.patch(
        "app.services.integration_service.google_play_scraper.app",
        side_effect=NotFoundError(),
    )
    source = GooglePlayReviewSource()
    with pytest.raises(AppNotFoundError):
        source.get_app_metadata("com.nonexistent.app")


def test_get_app_metadata_returns_title_score_and_total_reviews(mocker):
    mocker.patch(
        "app.services.integration_service.google_play_scraper.app",
        return_value={"title": "Example App", "score": 4.3, "reviews": 12345},
    )
    source = GooglePlayReviewSource()
    metadata = source.get_app_metadata("com.example.app")
    assert metadata == {"title": "Example App", "score": 4.3, "total_reviews": 12345}


def test_fetch_reviews_raises_app_not_found_when_app_missing(mocker):
    mocker.patch(
        "app.services.integration_service.google_play_scraper.app",
        side_effect=NotFoundError(),
    )
    source = GooglePlayReviewSource()
    with pytest.raises(AppNotFoundError):
        source.fetch_reviews("com.nonexistent.app", target_count=10)


def test_fetch_reviews_pages_until_target_count_reached(mocker):
    mocker.patch("app.services.integration_service.google_play_scraper.app", return_value={})
    mocker.patch("time.sleep", return_value=None)

    page_1 = [_fake_review(str(i)) for i in range(5)]
    page_2 = [_fake_review(str(i)) for i in range(5, 8)]

    class Token:
        def __init__(self, value):
            self.token = value

    mock_reviews = mocker.patch("app.services.integration_service.google_play_scraper.reviews")
    mock_reviews.side_effect = [
        (page_1, Token("cont")),
        (page_2, Token(None)),
    ]

    source = GooglePlayReviewSource()
    reviews, hit_cap = source.fetch_reviews("com.example.app", target_count=8)
    assert len(reviews) == 8
    assert reviews[0].review_id == "0"
    assert mock_reviews.call_count == 2
    assert hit_cap is True


def test_fetch_reviews_stops_at_date_cutoff_before_target_count(mocker):
    mocker.patch("app.services.integration_service.google_play_scraper.app", return_value={})
    mocker.patch("time.sleep", return_value=None)

    # Newest-first page: reviews 0-2 are within range, review 3 is too old,
    # review 4 (never reached) would also be within range if we kept going.
    page = [
        _fake_review("0", at=datetime(2026, 1, 10)),
        _fake_review("1", at=datetime(2026, 1, 9)),
        _fake_review("2", at=datetime(2026, 1, 8)),
        _fake_review("3", at=datetime(2025, 12, 1)),
        _fake_review("4", at=datetime(2025, 11, 1)),
    ]

    class Token:
        def __init__(self, value):
            self.token = value

    mocker.patch(
        "app.services.integration_service.google_play_scraper.reviews",
        return_value=(page, Token(None)),
    )

    source = GooglePlayReviewSource()
    reviews, hit_cap = source.fetch_reviews(
        "com.example.app", target_count=100, since=datetime(2026, 1, 1)
    )
    assert [r.review_id for r in reviews] == ["0", "1", "2"]
    assert hit_cap is False


def test_fetch_reviews_since_none_behaves_like_before(mocker):
    mocker.patch("app.services.integration_service.google_play_scraper.app", return_value={})
    mocker.patch("time.sleep", return_value=None)

    page = [_fake_review(str(i)) for i in range(5)]

    class Token:
        def __init__(self, value):
            self.token = value

    mocker.patch(
        "app.services.integration_service.google_play_scraper.reviews",
        return_value=(page, Token(None)),
    )

    source = GooglePlayReviewSource()
    reviews, hit_cap = source.fetch_reviews("com.example.app", target_count=5, since=None)
    assert len(reviews) == 5
    assert hit_cap is True


def test_fetch_reviews_hit_cap_false_when_source_runs_out_of_reviews(mocker):
    mocker.patch("app.services.integration_service.google_play_scraper.app", return_value={})
    mocker.patch("time.sleep", return_value=None)

    # App only has 3 reviews total, far fewer than the requested target_count.
    page = [_fake_review(str(i)) for i in range(3)]

    class Token:
        def __init__(self, value):
            self.token = value

    mocker.patch(
        "app.services.integration_service.google_play_scraper.reviews",
        return_value=(page, Token(None)),
    )

    source = GooglePlayReviewSource()
    reviews, hit_cap = source.fetch_reviews("com.example.app", target_count=100, since=None)
    assert len(reviews) == 3
    assert hit_cap is False


def test_fetch_reviews_raises_after_retries_exhausted(mocker):
    mocker.patch("app.services.integration_service.google_play_scraper.app", return_value={})
    mocker.patch("time.sleep", return_value=None)
    mocker.patch(
        "app.services.integration_service.google_play_scraper.reviews",
        side_effect=RuntimeError("network error"),
    )
    source = GooglePlayReviewSource()
    with pytest.raises(ReviewRetrievalError):
        source.fetch_reviews("com.example.app", target_count=10)
