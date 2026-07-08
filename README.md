# InsightQT

AI-powered Product Intelligence platform. Paste a Google Play Store app URL and get a structured Product Intelligence Report — sentiment, top customer problems, feature requests, and critical issues, every insight backed by real customer review excerpts.

Access is restricted to specific authorized users (see [Authentication](#authentication) below) — this isn't an open public tool.

**Live app:** https://insightqt-cyffdkuk5mfwgpimwvhqgd.streamlit.app/

## Setup

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

Add two things to `.env`:

```
GROQ_API_KEY=gsk_...
DATABASE_URL=postgresql://...
```

**`GROQ_API_KEY`** — a free [Groq](https://console.groq.com/keys) API key (no credit card required). AI analysis runs on Groq's free tier (`meta-llama/llama-4-scout-17b-16e-instruct`), which allows 30 requests/min and 30K tokens/min. Batches are sized and paced to stay within that, so a full analysis still takes a few minutes.

**`DATABASE_URL`** — a Postgres connection string, used to store authorized users (see below). The deployed app uses a hosted [Supabase](https://supabase.com) Postgres database, via its **Transaction pooler** connection string (the "Direct connection" variant is IPv6-only and won't reach from platforms without IPv6 egress, like Streamlit Community Cloud).

On the app lookup screen, pick a date range to analyze (Last 1/3/7/30 days, or All time). Only the most recent 500 reviews within that range are ever analyzed — if the range has fewer than 500 reviews, every review in range is analyzed.

## Authentication

The app is gated behind a login screen backed by a `users` table in Postgres (passwords stored as bcrypt hashes, never plain text). On first run with an empty `users` table, the app shows a one-time "create the first admin account" screen instead of a login form. From then on:

- Anyone without an account sees a login screen and can't get further.
- Admins get a **🔑 Admin** page (sidebar) to add or remove authorized users, and to grant/revoke admin access. There's always a safeguard against removing the last remaining admin.

## Run

```bash
streamlit run app/main.py
```

## Test

```bash
pytest tests/
```

Tests exercise real SQL against a local Postgres instance (not SQLite), so test behavior matches production. One-time local setup, if you don't already have Postgres running:

```bash
sudo apt-get install -y postgresql postgresql-contrib
sudo -u postgres psql -c "CREATE USER insightqt_test WITH PASSWORD 'testpass123';"
sudo -u postgres psql -c "CREATE DATABASE insightqt_test OWNER insightqt_test;"
```

## Deployment

Hosted on **Streamlit Community Cloud**, connected directly to this GitHub repo. Pushing to `main` auto-redeploys — there's no separate manual deploy step. `GROQ_API_KEY` and `DATABASE_URL` are configured as secrets in the Streamlit Cloud app's settings (not committed anywhere).

A GitHub Actions workflow (`.github/workflows/tests.yml`) runs the full test suite on every push, so a broken change is flagged before (or alongside) it reaching the live app.

## Scope (Sprint 0)

Google Play Store only. Apple App Store support is a planned second pass (see the project's Decision Log) — the integration layer already defines a `ReviewSource` interface so it can be added without refactoring.
