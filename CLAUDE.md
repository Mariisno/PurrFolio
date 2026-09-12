# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project does

PurrFolio has two surfaces built on the same market data:

1. **Discord bot** (`robot.py`) — a scheduled Python bot that fetches live cryptocurrency prices from the Norwegian exchange [Firi](https://firi.com), feeds them to Google Gemini AI for a brief Norwegian-language market commentary, and posts the result to a Discord channel via webhook.
2. **Portfolio dashboard** (`dashbord.py`) — a local web dashboard showing the owner's holdings (crypto plus stocks/funds) with live prices, NOK values, allocation and unrealised gain/loss.

## Running

```bash
pip install -r requirements.txt

# Discord-roboten
GEMINI_API_KEY=<key> DISCORD_WEBHOOK=<url> python robot.py

# Porteføljedashbordet (åpner http://127.0.0.1:8000)
cp portefolje.eksempel.json portefolje.json
python dashbord.py
```

No test suite or linter is configured.

## Architecture

- `markeder.py` — all market data lives here, shared by both surfaces.
  - `hent_firi_kryptoer(onskede_symboler)` hits the public Firi REST endpoint `/v2/markets/tickers`, filters for the requested symbols priced in NOK, and computes a mid-price from bid/ask. Defaults to the six symbols the Discord bot tracks (`STANDARD_KRYPTO`).
  - `hent_yahoo_kurser(tickere)` reads last price, previous close and currency from yfinance, falling back to `history()` when `fast_info` is empty. One dead ticker never breaks the rest.
  - `hent_valutakurser(valutaer)` fetches `<VALUTA>NOK=X` rates so non-NOK instruments can be converted.
- `robot.py` — `kjor_robot()` fetches crypto, builds a Norwegian prompt, sends it to `gemini-2.5-flash` via `google.genai`, then POSTs the formatted result to `DISCORD_WEBHOOK`.
- `portefolje.py` — reads and validates `portefolje.json` (`les_portefolje`), prices every holding and computes values, 24h change, gain/loss, per-type subtotals and allocation (`beregn_portefolje`). Holdings that cannot be priced are kept in the output with `mangler_kurs: true` and excluded from the totals, with a message in `advarsler`.
- `dashbord.py` — a stdlib `ThreadingHTTPServer` bound to 127.0.0.1 that serves `web/` plus `GET /api/portefolje`. `Kursbuffer` caches the computed portfolio for 30 seconds and invalidates on `portefolje.json` mtime, so edits show up without a restart.
- `web/` — the frontend: `index.html`, `stil.css`, `app.js`. Vanilla JS, no build step and no external requests; it polls `/api/portefolje` every 30 seconds and skips polling while the tab is hidden.

## Portfolio data

`portefolje.json` holds the owner's positions and is gitignored — `portefolje.eksempel.json` is the committed template. `snittpris` is given in the instrument's own trading currency; cost basis is converted to NOK with today's FX rate, so the currency effect on foreign holdings is an approximation. See README.md for the field reference.

## Dashboard visuals

Chart colours come from a validated categorical palette (eight fixed slots, separate steps for light and dark mode) defined as CSS custom properties in `web/stil.css`. Keep the slot order — it is what makes adjacent segments distinguishable under colour-vision deficiency. Direction is always carried by an arrow and a sign in addition to colour, never by colour alone.

## Secrets

Both `GEMINI_API_KEY` and `DISCORD_WEBHOOK` are injected as environment variables. Locally, export them before running. In CI, they are stored as GitHub repository secrets. The dashboard needs no secrets — it only reads public endpoints and a local file.

## CI / GitHub Actions

`.github/workflows/run_bot.yml` currently runs on manual `workflow_dispatch` only (the hourly cron is commented out). It uses Python 3.12 and installs dependencies with `pip install -r requirements.txt`. Only the Discord bot runs in CI; the dashboard is local-only by design.

## Code conventions

All identifiers, comments, and user-facing strings are written in Norwegian (Bokmål). Maintain this convention when adding or modifying code.
