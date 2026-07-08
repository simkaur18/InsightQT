# InsightQT

AI-powered Product Intelligence platform. Paste a Google Play Store app URL and get a structured Product Intelligence Report — sentiment, top customer problems, feature requests, and critical issues, every insight backed by real customer review excerpts.

## Setup

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

Add a free [Groq](https://console.groq.com/keys) API key to `.env` (no credit card required):

```
GROQ_API_KEY=gsk_...
```

AI analysis runs on Groq's free tier (`meta-llama/llama-4-scout-17b-16e-instruct`),
which allows 30 requests/min and 30K tokens/min. Batches are sized and paced to
stay within that, so a full analysis still takes a few minutes.

On the app lookup screen, pick a date range to analyze (Last 1/3/7/30 days, or
All time). Only the most recent 500 reviews within that range are ever
analyzed — if the range has fewer than 500 reviews, every review in range is
analyzed.

## Run

```bash
streamlit run app/main.py
```

## Test

```bash
pytest tests/
```

## Scope (Sprint 0)

Google Play Store only. Apple App Store support is a planned second pass (see the project's Decision Log) — the integration layer already defines a `ReviewSource` interface so it can be added without refactoring.
