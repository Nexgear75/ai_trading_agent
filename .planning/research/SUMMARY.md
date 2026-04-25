# Project Research Summary

**Project:** AI Trading Bot Dashboard
**Domain:** Real-time crypto paper trading visualization & control
**Researched:** 2026-04-25
**Confidence:** HIGH

## Executive Summary

This is a single-user web dashboard for monitoring and controlling an AI-powered crypto paper trading bot. The product sits in a well-established domain — Freqtrade, 3Commas, and Hummingbot have all solved similar problems — but this dashboard is differentiated by its tight integration with an existing ML pipeline (CNN-BiLSTM-AM model) and its focus on real-time visibility into model predictions. The recommended architecture is a React + Vite frontend communicating with a FastAPI backend via REST (historical data, bot commands) and WebSocket (real-time events), with SQLite for persistence and Supabase Auth for authentication. The frontend calls Binance REST API directly for chart data, keeping the backend focused on trading engine orchestration and event broadcasting.

The biggest risk is the async migration of the existing synchronous `RealtimeTrading` class. The current codebase uses threading locks, JSON file persistence, and a terminal UI (Rich library). Porting this to an async event-driven architecture with SQLite persistence and WebSocket push introduces concurrency pitfalls — specifically, blocking the event loop with model inference and race conditions on Binance WebSocket reconnection. Both must be mitigated from day one: `asyncio.to_thread()` for inference and engine-pause-on-disconnect for reconnection recovery.

## Key Findings

### Recommended Stack

All stack decisions were pre-validated in PROJECT.md and confirmed through research. The stack is pragmatic: SQLite over PostgreSQL (single-user simplicity), Lightweight Charts over D3/Chart.js (purpose-built for financial charts, ~40KB), and FastAPI over Flask (native async + WebSocket). The existing codebase already uses ccxt, PyTorch, pandas, and scikit-learn — these carry forward unchanged.

**Core technologies:**
- **React 19 + Vite 6 + TypeScript 5**: UI framework — largest ecosystem, fastest DX, type safety for WebSocket messages
- **Lightweight Charts 5**: Candlestick chart rendering — TradingView's open-source lib, native candlestick/markers/panes
- **FastAPI 0.115+ + Uvicorn**: Backend — async-native, built-in WebSocket, auto OpenAPI docs
- **SQLite 3 + aiosqlite**: Persistence — single-file DB, no external service, WAL mode for concurrent reads
- **Supabase Auth**: Authentication — managed JWT flow, no custom auth code, free tier sufficient
- **TailwindCSS 4 + zustand + react-query**: Frontend tooling — utility CSS, lightweight WS state, server state caching
- **Docker Compose + Nginx**: Deployment — reproducible VPS deployment, SSL termination, WS proxy

### Expected Features

The feature landscape is well-defined because the existing `realtime_testing.py` already implements a terminal version of the dashboard. The web dashboard is primarily a port with visual enhancements.

**Must have (table stakes):**
- Candlestick chart with real-time updates + trade markers — core value: see what the bot is doing
- Start/Stop/Restart controls — must be able to control the bot lifecycle
- Open positions table + closed trades history — know the bot's state
- Portfolio metrics (capital, PnL, win rate, drawdown) — at-a-glance health
- Crypto selector (single asset at a time) — switch between BTC, ETH, SOL
- SL/TP price lines on chart — visualize where positions will close
- Login/Auth protection — Supabase PKCE flow, JWT validation on backend
- Dark theme — financial dashboards are universally dark
- Binance connection status indicator — know if live data is flowing

**Should have (differentiators):**
- Model prediction visualization — show *why* the bot opened a position
- Risk management status panel — make circuit breaker/cooldown visible
- Trade execution timeline — chronological event log (matches existing terminal)
- Drawdown visualization — gauge or progress bar with warning thresholds

**Defer (v2+):**
- Equity curve — requires `portfolio_snapshots` accumulation over time, no historical data yet
- Configurable risk parameters from UI — edge cases in mid-run config changes
- Push notifications (Telegram/Discord) — not core value
- Live trading — safety-first, paper trading only in v1
- Multi-asset simultaneous trading — architecture must allow it but don't implement it

### Architecture Approach

The architecture follows an event-driven pattern: the Trading Engine emits typed events (KLINE, PREDICTION, ORDER_OPENED, ORDER_CLOSED, CIRCUIT_BREAKER) that the WebSocket Manager broadcasts to connected browsers. The frontend owns chart data (calls Binance REST directly), the backend owns trading state (SQLite is the single source of truth, replacing JSON files). This separation eliminates the backend-as-proxy anti-pattern and reduces latency for chart updates.

**Major components:**
1. **React Frontend** — UI rendering, chart visualization (Lightweight Charts), client state (zustand), server state (react-query), direct Binance REST for candles
2. **FastAPI REST Layer** — Bot control commands (start/stop/restart), historical data queries, config CRUD
3. **FastAPI WebSocket Manager** — Push real-time trading events, STATE_SNAPSHOT on connect/reconnect, heartbeat
4. **Trading Engine Service** — Async port of `RealtimeTrading`, runs inference loop, manages positions, emits events, pauses on Binance disconnect
5. **SQLite Database (WAL mode)** — Positions, trades, bot_config, bot_state — single source of truth
6. **Supabase Auth** — Login flow (frontend), JWT verification (backend middleware, python-jose + JWKS cache)

### Critical Pitfalls

1. **Blocking the async event loop with model inference** — Run `model.predict()` via `asyncio.to_thread()` from the start. PyTorch inference blocks 5-50ms, stalling WebSocket broadcasts.
2. **Race condition on Binance WS reconnect** — Pause the trading engine on disconnect; on reconnect, fetch missing history, check SL/TP against current price, then resume. Never process events during state recovery.
3. **Frontend WebSocket disconnect during active trade** — Send `STATE_SNAPSHOT` on every WS connect/reconnect. Frontend reconciles by replacing entire local state. Buffer last 100 events on backend.
4. **SQLite write contention without WAL mode** — Enable `PRAGMA journal_mode=WAL` + `PRAGMA synchronous=NORMAL`. Add indexes on `closed_trades(symbol, exit_date)` and `positions(symbol)`.
5. **Binance rate limiting on rapid symbol switches** — Debounce selector (500ms), cancel in-flight requests (AbortController), cache per-symbol candle data, pause fetches when tab hidden.

## Implications for Roadmap

Based on combined research, the following phase structure respects dependency chains and mitigates the most critical pitfalls early.

### Phase 1: Project Scaffolding & Database Layer
**Rationale:** Everything depends on the database schema and project structure. Setting up SQLite with WAL mode, proper indexes, and the core tables first prevents the write-contention pitfall (Pitfall #4) and gives all subsequent phases a persistence layer to build on. Auth also comes first because every endpoint needs JWT validation.
**Delivers:** Vite+React+TS project, FastAPI project skeleton, SQLite schema + migrations, Supabase Auth (login page + JWT middleware), Docker Compose skeleton
**Addresses:** Auth protection, database persistence (replaces JSON files)
**Avoids:** SQLite lock contention (WAL + indexes from day 1), JWKS cache miss (cache from day 1)

### Phase 2: Trading Engine Async Port
**Rationale:** The Trading Engine is the core backend service. It must be ported to async before the WebSocket layer or REST endpoints can be built on top of it. This is the highest-risk phase because it transforms the synchronous `RealtimeTrading` class into an async event-emitting service. Getting inference offloading and reconnect handling right here prevents the two most critical pitfalls.
**Delivers:** Async `TradingEngine` class, `asyncio.to_thread()` for model inference, Binance WS stream with async reconnect + engine pause, `TradingEvent` dataclass system, event queue (`asyncio.Queue`)
**Uses:** Existing `realtime_testing.py` as reference, ccxt, PyTorch model + scalers
**Implements:** Event-Driven Trading Engine pattern, Single Source of Truth (writes to SQLite)
**Avoids:** Blocking event loop (asyncio.to_thread from start), reconnect race condition (pause-on-disconnect from start)

### Phase 3: Backend API & WebSocket Layer
**Rationale:** With the Trading Engine emitting events and writing to SQLite, the REST and WebSocket layers expose this to the frontend. REST for commands and historical queries; WebSocket for real-time event push. STATE_SNAPSHOT on reconnect is critical here.
**Delivers:** FastAPI REST endpoints (start/stop/restart, positions, trades, metrics, config), WebSocket Manager with STATE_SNAPSHOT on connect, event buffer (last 100), heartbeat, Pydantic response models matching frontend TypeScript types
**Implements:** WebSocket Reconnection with Backoff pattern, STATE_SNAPSHOT on reconnect
**Avoids:** Lost events during client disconnect (STATE_SNAPSHOT + event buffer)

### Phase 4: Frontend Dashboard — Core UI
**Rationale:** With the backend fully operational, build the dashboard UI. Start with the chart (core value) and essential controls/metrics. This phase delivers the MVP: users can see the bot trading on a live chart and control it.
**Delivers:** Candlestick chart (Lightweight Charts v5) with live updates from Binance REST, trade markers (BUY/SELL arrows), SL/TP price lines, Start/Stop/Restart controls, crypto selector (debounced), open positions table, closed trades table, portfolio metrics bar, Binance connection status indicator, dark theme
**Addresses:** All table-stakes features from FEATURES.md
**Avoids:** Binance rate limiting (debounce + cache + AbortController), ms-vs-seconds timestamp bug (normalize at fetch boundary)

### Phase 5: Frontend Polish & Differentiators
**Rationale:** With MVP shipping, add the differentiator features that make the dashboard genuinely useful beyond basic monitoring. These features surface the model's reasoning and the risk management state — both unique to this bot.
**Delivers:** Model prediction visualization (predicted return near trade markers), risk management status panel (circuit breaker, cooldown, daily trade count), trade execution timeline (color-coded event log), drawdown visualization (gauge with thresholds), responsive layout polish (1280px+ focused)
**Addresses:** Differentiator features from FEATURES.md

### Phase 6: Docker Deployment & Hardening
**Rationale:** Deployment is last because the app needs to work locally first. Docker Compose ties frontend (Nginx serving built React), backend (FastAPI + Uvicorn), and SQLite volume together. This phase catches deployment-specific issues (Nginx WS proxy, MPS→CPU fallback, volume persistence).
**Delivers:** Docker Compose config, Nginx config (static serving + API proxy + WS proxy + SSL), SQLite volume mount, backup procedure documentation, CPU-only inference validation, production build + deploy script
**Avoids:** SQLite data loss on container recreation (volume mount), Nginx WS 400 (Upgrade headers), MPS unavailability in Docker (CPU device fallback)

### Phase Ordering Rationale

- **Database + Auth first (Phase 1):** Every other phase reads/writes state. Schema must exist before the engine, API, or frontend can function. Auth gates all access.
- **Trading Engine before API (Phase 2 → 3):** The engine is the source of events. The API layer is a consumer. Building API first would require mocking the engine, creating throwaway code.
- **Backend before Frontend (Phase 3 → 4):** Frontend needs real REST endpoints and WebSocket events. Mocking creates technical debt; real backend enables real integration testing.
- **Core UI before Polish (Phase 4 → 5):** Chart + controls + metrics = the product. Differentiators are additive and can ship incrementally.
- **Deployment last (Phase 6):** Local-first development is faster. Docker adds config complexity that shouldn't slow down feature development.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2 (Trading Engine):** Complex async migration from threading to asyncio. The existing `BinanceKlineStream` uses `threading.Thread` — needs careful design for the thread-to-async bridge via `asyncio.Queue`. Needs `/gsd-research-phase` for the specific async patterns.
- **Phase 4 (Frontend Core UI):** Lightweight Charts v5 API for markers, price lines, and pane configuration. While well-documented, the specific integration patterns (markers on candle updates, price lines that follow position changes) need verification. Consider `/gsd-research-phase` for LWC v5 marker primitives.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Scaffolding & DB):** Well-documented: SQLite schema, Supabase Auth setup, Vite project init. All have extensive official docs.
- **Phase 3 (Backend API):** Standard FastAPI REST + WebSocket patterns. Well-documented in official docs.
- **Phase 5 (Polish):** Pure React UI work. No novel integrations.
- **Phase 6 (Deployment):** Standard Docker Compose + Nginx. Well-documented.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All decisions pre-validated in PROJECT.md. Official docs confirm capabilities (LWC v5 markers/panes, FastAPI WebSocket, Supabase Auth JWT flow). Competitive analysis (Freqtrade) validates similar stack choices. |
| Features | HIGH | Feature inventory sourced from existing `realtime_testing.py` — the terminal dashboard already implements most features. Mapping from terminal → web is well-understood. |
| Architecture | HIGH | Event-driven pattern is standard for real-time dashboards. Freqtrade uses identical architecture (Python backend + WebSocket + Vue frontend). Anti-patterns are well-documented. |
| Pitfalls | HIGH | All 5 critical pitfalls are derived from the existing codebase (threading model, JSON persistence, reconnect handling) and official docs (SQLite WAL, Binance rate limits, WebSocket reconnect). Preventions are concrete with code examples. |

**Overall confidence:** HIGH

### Gaps to Address

- **Binance WebSocket from browser vs. backend:** The architecture diagram shows the frontend calling Binance REST for chart data, but the architecture also implies the backend's Binance WS stream (ccxt) feeds the trading engine. The frontend could optionally connect to Binance WS directly for live candle updates (avoiding backend relay). This decision should be made during Phase 4 planning — does the frontend subscribe to Binance WS for live chart ticks, or does it rely on the backend's KLINE events?
- **Model registry integration:** The existing codebase has a `registry.get_predictor()` system. The Trading Engine needs to use this instead of the manual `predict_return()` in `realtime_testing.py`. This refactor is straightforward but needs to be specified in Phase 2 planning.
- **State recovery granularity on reconnect:** The STATE_SNAPSHOT approach (full state replacement on reconnect) is simple but may cause UI flicker if the frontend re-renders everything. Consider a diff-based approach for Phase 5 optimization. Not a blocker for MVP.

## Sources

### Primary (HIGH confidence)
- PROJECT.md — All stack decisions, requirements, scope boundaries
- Existing `testing/realtime_testing.py` — Feature inventory, threading model, state persistence, event loop patterns
- Existing `testing/config.json` — Risk management parameters
- TradingView Lightweight Charts v5 docs — https://tradingview.github.io/lightweight-charts/ — candlestick, markers, panes
- FastAPI WebSocket docs — https://fastapi.tiangolo.com/advanced/websockets/ — native WebSocket, connection management
- Supabase Auth docs — https://supabase.com/docs/guides/auth — JWT validation flow, PKCE
- SQLite WAL mode docs — https://www.sqlite.org/wal.html — concurrent access patterns
- Binance API docs — Rate limits, timestamp format, klines endpoint

### Secondary (MEDIUM confidence)
- Freqtrade architecture — Vue.js + Python backend + WebSocket (validates pattern choice)
- Docker docs — Volume mounts, Compose networking

### Tertiary (LOW confidence)
- None — all findings are backed by primary sources

---
*Research completed: 2026-04-25*
*Ready for roadmap: yes*
