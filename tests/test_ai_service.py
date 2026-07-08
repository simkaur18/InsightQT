import json
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.exceptions import MissingAPIKeyError
from app.models import CleanReview, SourcePlatform
from app.services import ai_service
from app.services.ai_service import (
    AggregatedReport,
    BatchExtraction,
    CriticalTopItem,
    FeatureRequestItem,
    OverallSentiment,
    PositiveHighlightItem,
    SentimentCounts,
    ThemeItem,
    TopItem,
)


@pytest.fixture(autouse=True)
def _no_real_sleep(mocker):
    mocker.patch("app.services.ai_service.time.sleep", return_value=None)
    mocker.patch("app.utils.helpers.time.sleep", return_value=None)


def _clean_review(review_id: str) -> CleanReview:
    return CleanReview(
        review_id=review_id,
        author="Author",
        rating=5,
        text="Great app, works well.",
        date=datetime(2026, 1, 1),
        language="en",
        source=SourcePlatform.GOOGLE_PLAY,
    )


def _fake_batch_extraction(review_ids: list[str]) -> BatchExtraction:
    return BatchExtraction(
        sentiment_counts=SentimentCounts(positive=1, neutral=0, negative=0),
        themes=[ThemeItem(name="Great UX", sentiment="positive", review_ids=review_ids)],
        feature_requests=[
            FeatureRequestItem(description="Add dark mode", review_ids=review_ids)
        ],
        positive_highlights=[
            PositiveHighlightItem(description="Fast and reliable", review_ids=review_ids)
        ],
        critical_issues=[],
    )


def _groq_response_with_json(payload: dict):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload)))]
    )


def test_get_client_raises_missing_api_key_when_unset(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(MissingAPIKeyError):
        ai_service.get_client()


def test_analyze_reviews_in_batches_reports_progress_and_tolerates_failures(mocker):
    reviews = [_clean_review(str(i)) for i in range(5)]
    mocker.patch.object(ai_service, "get_client", return_value=MagicMock())

    call_count = {"n": 0}

    def fake_extract_batch(client, batch):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("simulated batch failure")
        return _fake_batch_extraction([r.review_id for r in batch])

    mocker.patch.object(ai_service, "extract_batch", side_effect=fake_extract_batch)
    mocker.patch.object(ai_service, "AI_BATCH_SIZE", 2)

    progress_calls = []
    results, total, failed = ai_service.analyze_reviews_in_batches(
        reviews, progress_callback=lambda done, tot: progress_calls.append((done, tot))
    )

    assert total == 3  # 5 reviews / batch size 2 -> 3 batches (2,2,1)
    assert failed == 1
    assert len(results) == total - failed
    assert len(progress_calls) == total


def test_extract_batch_calls_groq_with_json_schema_and_parses_response(mocker):
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _groq_response_with_json(
        _fake_batch_extraction(["1", "2"]).model_dump()
    )

    reviews = [_clean_review("1"), _clean_review("2")]
    result = ai_service.extract_batch(mock_client, reviews)

    assert isinstance(result, BatchExtraction)
    assert result.themes[0].review_ids == ["1", "2"]

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["response_format"]["type"] == "json_schema"
    assert call_kwargs["response_format"]["json_schema"]["name"] == "BatchExtraction"


def test_aggregate_batches_returns_parsed_output(mocker):
    mock_client = MagicMock()
    aggregated = AggregatedReport(
        executive_summary="Users love the app overall.",
        overall_sentiment=OverallSentiment(positive_pct=80.0, neutral_pct=15.0, negative_pct=5.0),
        top_problems=[],
        feature_requests=[
            TopItem(title="Dark mode", frequency=3, representative_review_ids=["1", "2"])
        ],
        positive_feedback=[],
        critical_issues=[
            CriticalTopItem(
                title="Crash on startup", severity="high", representative_review_ids=["3"]
            )
        ],
    )
    mock_client.chat.completions.create.return_value = _groq_response_with_json(
        aggregated.model_dump()
    )
    mocker.patch.object(ai_service, "get_client", return_value=mock_client)

    result = ai_service.aggregate_batches([_fake_batch_extraction(["1", "2", "3"])])

    assert result.executive_summary == "Users love the app overall."
    assert result.feature_requests[0].title == "Dark mode"
    mock_client.chat.completions.create.assert_called_once()


def test_extract_batch_retries_then_raises_on_persistent_malformed_json(mocker):
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="not valid json"))]
    )
    mocker.patch.object(ai_service, "AI_MAX_RETRIES", 2)

    with pytest.raises(Exception):
        ai_service.extract_batch(mock_client, [_clean_review("1")])

    assert mock_client.chat.completions.create.call_count == 2
