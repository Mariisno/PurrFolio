# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project does

PurrFolio is a scheduled Python bot that fetches live cryptocurrency prices from the Norwegian exchange [Firi](https://firi.com), feeds them to Google Gemini AI for a brief Norwegian-language market commentary, and posts the result to a Discord channel via webhook.

## Running the bot

```bash
pip install requests google-genai
GEMINI_API_KEY=<key> DISCORD_WEBHOOK=<url> python robot.py
```

No test suite or linter is configured.

## Architecture

Everything lives in a single file (`robot.py`) with two functions:

- `hent_firi_kryptoer()` — hits the public Firi REST endpoint `/v2/markets/tickers`, filters for the six tracked symbols (BTC, XRP, LTC, ETH, SOL, ADA) priced in NOK, and computes a mid-price from bid/ask.
- `kjor_robot()` — calls the above, builds a prompt in Norwegian, sends it to `gemini-2.5-flash` via `google.genai`, then POSTs the formatted result to `DISCORD_WEBHOOK`.

## Secrets

Both `GEMINI_API_KEY` and `DISCORD_WEBHOOK` are injected as environment variables. Locally, export them before running. In CI, they are stored as GitHub repository secrets.

## CI / GitHub Actions

`.github/workflows/run_bot.yml` runs on a cron (`0 8-20 * * *` — every hour from 08:00 to 20:59 UTC) and supports manual `workflow_dispatch`. It uses Python 3.12 and installs dependencies directly with `pip install requests yfinance google-genai`.

## Dependency note

`requirements.txt` currently lists `google-generativeai` (the legacy package), but the code imports `from google import genai`, which requires the newer `google-genai` package. The workflow already installs the correct package. `requirements.txt` should be updated to `google-genai>=0.3.0`.

## Code conventions

All identifiers, comments, and user-facing strings are written in Norwegian (Bokmål). Maintain this convention when adding or modifying code.
