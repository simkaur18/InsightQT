import re

import pandas as pd
from langdetect import DetectorFactory, LangDetectException, detect

from app.models import CleanReview, RawReview

DetectorFactory.seed = 0

_WHITESPACE_RE = re.compile(r"\s+")


def _clean_text(text: str) -> str:
    text = text.replace("\r\n", " ").replace("\n", " ")
    return _WHITESPACE_RE.sub(" ", text).strip()


def _detect_language(text: str) -> str:
    if not text or not text.strip():
        return "unknown"
    try:
        return detect(text)
    except LangDetectException:
        return "unknown"


def clean_reviews(raw_reviews: list[RawReview]) -> list[CleanReview]:
    """Clean, dedupe, and language-tag raw reviews.

    Dedupes by review_id first (exact source-level duplicates), then by
    cleaned text (near-duplicate reviews re-posted or re-scraped).
    """
    if not raw_reviews:
        return []

    df = pd.DataFrame(
        [
            {
                "review_id": r.review_id,
                "author": r.author,
                "rating": r.rating,
                "text": _clean_text(r.text),
                "date": r.date,
                "source": r.source,
            }
            for r in raw_reviews
        ]
    )

    df = df.drop_duplicates(subset="review_id", keep="first")
    df = df.drop_duplicates(subset="text", keep="first")

    clean_reviews_list: list[CleanReview] = []
    for row in df.itertuples(index=False):
        clean_reviews_list.append(
            CleanReview(
                review_id=row.review_id,
                author=row.author,
                rating=row.rating,
                text=row.text,
                date=row.date,
                language=_detect_language(row.text),
                source=row.source,
            )
        )

    return clean_reviews_list
