# AI Trading Bot Dashboard

## What This Is

A web-based dashboard to pilot an AI-powered crypto trading bot (CNN-BiLSTM-AM model) in Paper Trading mode. Users control the bot (start/stop/restart), monitor performance metrics in real-time (Win Rate, PnL, Drawdown, fees), and visualize trading decisions directly on financial charts. Built for deployment on a VPS via Docker with Supabase Auth for secure access.

## Core Value

The bot executes trades reliably and the dashboard shows exactly what it's doing — positions, PnL, and model predictions live on the chart. If nothing else works, real-time visibility into bot decisions must work.

## Requirements

### Validated

- ✓ ML pipeline fetches Binance data, builds features, trains CNN model — existing codebase
- ✓ CNN1D model trained with HuberLoss, RobustScaler, temporal split — existing codebase
- ✓ Backtesting engine simulates trades on historical data — existing codebase
- ✓ Realtime testing with live Binance data (realtime_testing.py) — existing codebase

### Active

- [ ] FastAPI backend orchestrates trading engine with WebSocket push to frontend
- [ ] SQLite database replaces JSON files for bot state, positions, and trade history
- [ ] Paper trading simulation with realistic slippage, Maker/Taker fees, and RRR-based SL/TP
- [ ] React + Vite dashboard with TradingView Lightweight Charts for candlestick rendering
- [ ] Real-time WebSocket connection displays bot events (ORDER_OPENED, ORDER_CLOSED, etc.)
- [ ] Supabase Auth secures dashboard access
- [ ] Docker + Docker Compose deployment for VPS
- [ ] Performance metrics display: Win Rate, total Profit, Drawdown, simulated fees
- [ ] Open positions table and closed trades history
- [ ] Crypto selector (single asset at a time)
- [ ] Start/Stop/Restart controls for trading engine

### Out of Scope

- Multi-crypto simultaneous support — deferred to v2, architecture must allow it
- Live trading with real Binance API keys — safety-first, paper trading only for v1
- Push notifications (Telegram/Discord) — nice-to-have, not core value
- Model retraining from the dashboard — separate concern, use CLI

## Context

- Existing Python codebase with ML pipeline: data fetching → feature engineering → model training → evaluation → backtesting → realtime testing
- The `realtime_testing.py` script is the current entry point for paper trading; this project wraps it in a web application
- CNN-BiLSTM-AM model already exists (or will be added to the existing CNN model); the dashboard is model-agnostic in architecture
- Binance API is accessed via `ccxt` library for market data
- Current state management uses JSON files — SQLite migration is part of this project
- Apple Silicon (MPS) support for model inference

## Constraints

- **Tech Stack**: React + Vite + TailwindCSS + Lightweight Charts (frontend), FastAPI + WebSockets (backend), SQLite (database), Supabase (auth), Docker (infra)
- **Deployment**: VPS Linux via Docker Compose — no serverless
- **Security**: Supabase Auth required — no unauthenticated access to dashboard
- **Data Source**: Binance API via ccxt — frontend calls Binance directly for chart data, backend for bot events
- **Model**: CNN-BiLSTM-AM (or existing CNN as fallback) — model inference on backend only
- **Single Asset**: One crypto at a time in v1

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| FastAPI over Flask | Native async + WebSocket support | — Pending |
| SQLite over PostgreSQL | Simpler VPS deployment, no external DB service | — Pending |
| Supabase Auth | Managed auth service, no custom auth logic | — Pending |
| Frontend calls Binance directly | Reduces backend load, faster chart rendering | — Pending |
| Docker Compose | Reproducible VPS deployment, single command start | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-25 after initialization*
