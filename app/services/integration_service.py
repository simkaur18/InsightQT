from abc import ABC, abstractmethod
from datetime import datetime

import google_play_scraper
from google_play_scraper.exceptions import NotFoundError

from app.exceptions import AppNotFoundError, ReviewRetrievalError
from app.models import RawReview, SourcePlatform
from app.utils.constants import (
    REVIEWS_PER_SCRAPE_PAGE,
    SCRAPE_MAX_RETRIES,
    SCRAPE_PAGE_DELAY_SECONDS,
)
from app.utils.helpers import retry_with_backoff


class ReviewSource(ABC):
    """Interface every app-store connector implements.

    A future AppleAppStoreReviewSource implements this same interface so the
    rest of the pipeline (processing/AI/report) never needs to know which
    platform the reviews came from.
    """

    @abstractmethod
    def validate_app_exists(self, app_id: str) -> bool: ...

    @abstractmethod
    def get_app_metadata(self, app_id: str) -> dict: ...

    @abstractmethod
    def fetch_reviews(
        self, app_id: str, target_count: int, since: datetime | None = None
    ) -> tuple[list[RawReview], bool]: ...


class GooglePlayReviewSource(ReviewSource):
    def validate_app_exists(self, app_id: str) -> bool:
        try:
            google_play_scraper.app(app_id)
            return True
        except NotFoundError:
            return False

    def get_app_metadata(self, app_id: str) -> dict:
        try:
            info = google_play_scraper.app(app_id)
        except NotFoundError as exc:
            raise AppNotFoundError(
                f"No app found on Google Play with ID '{app_id}'."
            ) from exc
        return {
            "title": info.get("title") or app_id,
            "score": float(info.get("score") or 0.0),
            "total_reviews": int(info.get("reviews") or 0),
        }

    def fetch_reviews(
        self, app_id: str, target_count: int, since: datetime | None = None
    ) -> tuple[list[RawReview], bool]:
        """Fetch up to target_count reviews, newest first.

        If since is given, stops as soon as a review older than that cutoff
        is encountered (reviews are returned newest-first, so this is a safe
        early exit rather than a post-hoc filter) — whichever limit
        (target_count or since) is hit first wins.

        Returns (reviews, hit_cap). hit_cap is True if target_count was
        reached before the date range (or available reviews) was exhausted —
        i.e. there may be more reviews in range than what's returned. It's
        False if we stopped because of the date cutoff or ran out of
        reviews entirely, meaning the returned list is the complete set for
        the requested range.
        """
        if not self.validate_app_exists(app_id):
            raise AppNotFoundError(
                f"No app found on Google Play with ID '{app_id}'. "
                "Check the URL and try again."
            )

        import time

        raw_reviews: list[RawReview] = []
        continuation_token = None
        hit_cap = False

        while len(raw_reviews) < target_count:
            remaining = target_count - len(raw_reviews)
            page_size = min(REVIEWS_PER_SCRAPE_PAGE, remaining)

            def _fetch_page():
                return google_play_scraper.reviews(
                    app_id,
                    count=page_size,
                    continuation_token=continuation_token,
                )

            try:
                page_reviews, continuation_token = retry_with_backoff(
                    _fetch_page,
                    max_retries=SCRAPE_MAX_RETRIES,
                    retry_on=(Exception,),
                )
            except Exception as exc:
                if raw_reviews:
                    # We already have some reviews — proceed with a partial set
                    # rather than discarding everything already retrieved.
                    break
                raise ReviewRetrievalError(
                    f"Failed to retrieve reviews for '{app_id}' after "
                    f"{SCRAPE_MAX_RETRIES} attempts: {exc}"
                ) from exc

            if not page_reviews:
                break

            hit_cutoff = False
            for review in page_reviews:
                review_date = review["at"]
                if since is not None and review_date < since:
                    hit_cutoff = True
                    break
                raw_reviews.append(
                    RawReview(
                        review_id=review["reviewId"],
                        author=review.get("userName") or "Anonymous",
                        rating=int(review.get("score") or 0),
                        text=review.get("content") or "",
                        date=review_date,
                        source=SourcePlatform.GOOGLE_PLAY,
                        app_version=review.get("reviewCreatedVersion"),
                        thumbs_up_count=int(review.get("thumbsUpCount") or 0),
                    )
                )
                if len(raw_reviews) >= target_count:
                    hit_cap = True
                    break

            if hit_cutoff or hit_cap:
                break

            if continuation_token is None or continuation_token.token is None:
                break

            time.sleep(SCRAPE_PAGE_DELAY_SECONDS)

        return raw_reviews[:target_count], hit_cap
