import json
import os
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

from groq import Groq
from pydantic import BaseModel, ConfigDict

from app.exceptions import MissingAPIKeyError
from app.models import CleanReview
from app.utils.constants import (
    AI_BATCH_DELAY_SECONDS,
    AI_BATCH_SIZE,
    AI_MAX_CONCURRENT_BATCHES,
    AI_MAX_RETRIES,
    AI_REVIEW_TEXT_MAX_CHARS,
    GROQ_MODEL,
)
from app.utils.helpers import retry_with_backoff


class _StrictModel(BaseModel):
    """Base for every schema sent to Groq's structured-output feature.

    extra="forbid" makes Pydantic emit additionalProperties: false in the
    generated JSON schema, which the model uses to constrain its output.
    """

    model_config = ConfigDict(extra="forbid")


class SentimentCounts(_StrictModel):
    positive: int
    neutral: int
    negative: int


class ThemeItem(_StrictModel):
    name: str
    sentiment: str
    review_ids: list[str]


class FeatureRequestItem(_StrictModel):
    description: str
    review_ids: list[str]


class PositiveHighlightItem(_StrictModel):
    description: str
    review_ids: list[str]


class CriticalIssueItem(_StrictModel):
    description: str
    severity: str
    review_ids: list[str]


class BatchExtraction(_StrictModel):
    sentiment_counts: SentimentCounts
    themes: list[ThemeItem]
    feature_requests: list[FeatureRequestItem]
    positive_highlights: list[PositiveHighlightItem]
    critical_issues: list[CriticalIssueItem]


class TopItem(_StrictModel):
    title: str
    frequency: int
    representative_review_ids: list[str]


class CriticalTopItem(_StrictModel):
    title: str
    severity: str
    representative_review_ids: list[str]


class OverallSentiment(_StrictModel):
    positive_pct: float
    neutral_pct: float
    negative_pct: float


class AggregatedReport(_StrictModel):
    executive_summary: str
    overall_sentiment: OverallSentiment
    top_problems: list[TopItem]
    feature_requests: list[TopItem]
    positive_feedback: list[TopItem]
    critical_issues: list[CriticalTopItem]


def get_client() -> Groq:
    if not os.getenv("GROQ_API_KEY"):
        raise MissingAPIKeyError(
            "GROQ_API_KEY is not set. Add it to your .env file to enable AI analysis."
        )
    return Groq()


def _chunk(reviews: list[CleanReview], size: int) -> list[list[CleanReview]]:
    return [reviews[i : i + size] for i in range(0, len(reviews), size)]


def _format_batch_for_prompt(batch: list[CleanReview]) -> str:
    lines = []
    for r in batch:
        text = r.text[:AI_REVIEW_TEXT_MAX_CHARS]
        lines.append(f'- id="{r.review_id}" rating={r.rating}: "{text}"')
    return "\n".join(lines)


def _call_structured(
    client: Groq,
    system_prompt: str,
    user_prompt: str,
    schema_model: type[BaseModel],
    max_tokens: int,
) -> BaseModel:
    def _do_call():
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": schema_model.__name__,
                    "strict": False,
                    "schema": schema_model.model_json_schema(),
                },
            },
        )
        content = response.choices[0].message.content
        return schema_model.model_validate_json(content)

    return retry_with_backoff(
        _do_call,
        max_retries=AI_MAX_RETRIES,
        base_delay_seconds=3.0,
        retry_on=(Exception,),
    )


_BATCH_SYSTEM_PROMPT = (
    "You are analyzing a batch of mobile app customer reviews for a Product Manager. "
    "For each theme, feature request, positive highlight, and critical issue you identify, "
    "include AT MOST 3 example review IDs (from the id=\"...\" field) that support it — "
    "never list every matching review, just a few representative examples. Review IDs are "
    "long strings; listing many of them wastes space needed for the actual analysis. "
    "Never invent a review ID that isn't in the input. Group similar reviews under one item "
    "rather than creating a near-duplicate item per review. Respond with JSON only."
)


def extract_batch(client: Groq, batch: list[CleanReview]) -> BatchExtraction:
    prompt = (
        "Analyze these customer reviews and extract sentiment, themes, feature requests, "
        "positive highlights, and critical issues:\n\n" + _format_batch_for_prompt(batch)
    )
    result = _call_structured(client, _BATCH_SYSTEM_PROMPT, prompt, BatchExtraction, max_tokens=1400)
    return result


def analyze_reviews_in_batches(
    reviews: list[CleanReview],
    progress_callback: Callable[[int, int], None] | None = None,
) -> tuple[list[BatchExtraction], int, int]:
    """Run Pass 1 (per-batch structured extraction).

    Runs with bounded concurrency (1 by default on the free tier, to respect
    Groq's per-minute token budget) and a fixed delay between batches.
    Returns (successful_extractions, total_batch_count, failed_batch_count).
    A failed batch is skipped, not fatal — the run continues with the rest.
    """
    client = get_client()
    batches = _chunk(reviews, AI_BATCH_SIZE)
    total = len(batches)
    results: list[BatchExtraction] = []
    failed = 0
    completed = 0

    def _run_batch(batch: list[CleanReview]) -> BatchExtraction:
        result = extract_batch(client, batch)
        time.sleep(AI_BATCH_DELAY_SECONDS)
        return result

    with ThreadPoolExecutor(max_workers=AI_MAX_CONCURRENT_BATCHES) as executor:
        futures = {executor.submit(_run_batch, batch): batch for batch in batches}
        for future in as_completed(futures):
            completed += 1
            try:
                results.append(future.result())
            except Exception:
                failed += 1
            if progress_callback:
                progress_callback(completed, total)

    return results, total, failed


_AGGREGATION_SYSTEM_PROMPT = (
    "You are synthesizing multiple batches of app-review analysis into a single "
    "Product Intelligence Report for a Product Manager. Merge near-duplicate themes "
    "across batches into one item (do not list the same underlying issue twice under "
    "slightly different titles), sum their frequencies, and select up to 5 "
    "representative review IDs per item from the union already provided — never "
    "invent a review ID. Write a concise, non-technical executive summary. "
    "overall_sentiment.positive_pct, neutral_pct, and negative_pct MUST be numbers "
    "from 0 to 100 (e.g. 33.3 for a third), NOT fractions from 0 to 1, and must sum "
    "to approximately 100. Respond with JSON only."
)


def aggregate_batches(batch_extractions: list[BatchExtraction]) -> AggregatedReport:
    client = get_client()
    batch_json = json.dumps(
        [b.model_dump() for b in batch_extractions], separators=(",", ":")
    )
    prompt = (
        "Merge and summarize these per-batch review analyses into a single report:\n\n"
        f"{batch_json}"
    )
    return _call_structured(
        client, _AGGREGATION_SYSTEM_PROMPT, prompt, AggregatedReport, max_tokens=2000
    )
