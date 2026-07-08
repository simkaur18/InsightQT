GROQ_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

# Switched from openai/gpt-oss-20b (8K TPM, and a hidden reasoning pass that
# silently ate over half the completion budget on real batches, causing
# truncated/invalid JSON and, combined with uncapped review-ID lists in the
# aggregation prompt, a 413 "too large" error in practice). This model has no
# reasoning tax and a much bigger budget: 30 req/min, 30K tokens/min. At the
# real per-call cost we measured (~2-5K tokens with review IDs capped at 3
# per item in the prompt — see _BATCH_SYSTEM_PROMPT), requests/min (not
# tokens/min) is now the binding constraint, hence the ~2s batch delay below.
# Single cap applied everywhere (date-bounded ranges and "All time" alike),
# so there's one honest number to disclose to the user: "only the most recent
# 500 reviews in your selected range are analyzed." At AI_BATCH_SIZE=20 this
# is 25 batches + 1 aggregation call — a few minutes even on Groq's free
# tier, and comfortably under its 1,000 requests/day quota. If the actual
# review count in range is under this cap, every review in range is analyzed
# (see GooglePlayReviewSource.fetch_reviews's hit_cap return value).
MAX_REVIEWS_TO_ANALYZE = 500

REVIEWS_PER_SCRAPE_PAGE = 100
SCRAPE_PAGE_DELAY_SECONDS = 0.3
SCRAPE_MAX_RETRIES = 3

# Ordered so it can be used directly as a selectbox's options list.
# Value is the number of days back from now; None means "no cutoff".
# "Last 90 days" removed 2026-07-08 (too wide for the current cap to feel
# meaningful on high-volume apps) — revisit if/when needed.
DATE_RANGE_PRESETS = {
    "Last 1 day": 1,
    "Last 3 days": 3,
    "Last 7 days": 7,
    "Last 30 days": 30,
    "All time": None,
}
DEFAULT_DATE_RANGE_PRESET = "Last 3 days"

AI_BATCH_SIZE = 20
AI_MAX_CONCURRENT_BATCHES = 1
# Free tier is 30 requests/min == 1 every 2s; add a small margin.
AI_BATCH_DELAY_SECONDS = 2.2
AI_REVIEW_TEXT_MAX_CHARS = 200
AI_MAX_RETRIES = 4

PROCESSING_STAGES = [
    "Validating URL",
    "Retrieving app reviews",
    "Cleaning & processing reviews",
    "Running AI sentiment analysis",
    "Detecting themes",
    "Generating product insights",
]
