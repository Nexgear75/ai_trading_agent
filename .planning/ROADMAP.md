# Roadmap: AI Trading Bot Dashboard

## Overview

Transform an existing ML-powered crypto paper trading bot (terminal-based) into a web dashboard where users control the bot and see exactly what it's doing in real-time. The journey: foundation (database + auth) → backend (trading engine + API) → frontend (chart, controls, metrics) → deployment (Docker + Nginx). Each phase builds on the previous, and by Phase 3 completion the core value is delivered — users see positions, PnL, and model predictions live on the chart.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3, 4): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

- [ ] **Phase 1: Foundation & Auth** — SQLite database, Alembic migrations, Supabase Auth (login + JWT)
- [ ] **Phase 2: Trading Engine & API** — Async trading engine, FastAPI REST + WebSocket layer
- [ ] **Phase 3: Dashboard UI** — Chart, controls, positions, metrics, dark theme
- [ ] **Phase 4: Docker Deployment** — Docker Compose, Nginx proxy, CPU-only PyTorch

## Phase Details

### Phase 1: Foundation & Auth

**Goal**: Users can log in securely and all application state persists in SQLite

**Depends on**: Nothing (first phase)

**Requirements**: INFRA-01, INFRA-02, AUTH-01, AUTH-02, AUTH-03, AUTH-04

**Success Criteria** (what must be TRUE):
1. User can log in via email/password through Supabase Auth and access the dashboard
2. Unauthenticated users are redirected to a login page and cannot access dashboard routes
3. User session persists across browser refreshes without requiring re-login
4. User can log out from any page and is returned to the login screen
5. SQLite database is initialized with bot_state, positions, trades, and portfolio_snapshots tables (WAL mode enabled) and all state mutations are queryable

**Plans**: TBD

**UI hint**: yes

### Phase 2: Trading Engine & API

**Goal**: The trading bot runs as an async service and all its state/events are accessible via REST and WebSocket

**Depends on**: Phase 1

**Requirements**: ENGN-01, ENGN-02, ENGN-03, ENGN-04, ENGN-05, ENGN-06, ENGN-07, API-01, API-02, API-03, API-04, API-05, API-06, API-07

**Success Criteria** (what must be TRUE):
1. User can start, stop, and restart the trading engine via REST endpoints and receive confirmation of each action
2. Trading engine runs independently — stays alive and processes Binance data even when no browser is connected
3. Model inference runs without blocking the event loop — WebSocket events continue flowing during prediction
4. Binance WebSocket reconnects automatically on disconnect and the engine pauses trading during reconnection recovery
5. A connected browser receives real-time events (ORDER_OPENED, ORDER_CLOSED, CANDLE_CLOSED, PREDICTION, CIRCUIT_BREAKER, STATE_SNAPSHOT) via WebSocket
6. On browser connect/reconnect, a full STATE_SNAPSHOT is received immediately, hydrating the UI without waiting for next event
7. All API and WebSocket endpoints reject unauthenticated requests (Supabase JWT validation)
8. Paper trades execute with realistic slippage, Maker/Taker fees, and RRR-based Stop-Loss/Take-Profit

**Plans**: TBD

### Phase 3: Dashboard UI

**Goal**: Users see the bot's trading decisions live on a financial chart and can control it from the dashboard

**Depends on**: Phase 2

**Requirements**: CHRT-01, CHRT-02, CHRT-03, CHRT-04, CHRT-05, CHRT-06, CTRL-01, CTRL-02, CTRL-03, CTRL-04, DATA-01, DATA-02, DATA-03, DATA-04, THEME-01, THEME-02

**Success Criteria** (what must be TRUE):
1. User sees a candlestick chart with historical candles loaded on mount and new candles appearing in real-time
2. Trade markers (arrows) appear on the chart at the exact candle where BUY/SELL orders were executed
3. Stop-Loss and Take-Profit price lines are visible on the chart for any open position
4. User can start, stop, and restart the bot using dashboard controls, and sees the bot status change immediately
5. User can switch the active trading symbol via a dropdown and the bot restarts on the new pair
6. Open positions table shows direction, entry price, SL, TP, unrealized PnL, and allocated capital for each position
7. Closed trades history shows entry/exit dates, prices, net PnL, fees, and exit reason
8. Portfolio metrics cards display capital, allocated capital, portfolio value, total PnL, and win rate
9. Dark theme is applied consistently across chart, controls, tables, and all dashboard elements
10. Binance connection status is visible (ONLINE/RECONNECTING/OFFLINE) and bot status indicator shows RUNNING/STOPPED/ERROR

**Plans**: TBD

**UI hint**: yes

### Phase 4: Docker Deployment

**Goal**: The entire application deploys on a VPS via a single `docker compose up` command

**Depends on**: Phase 3

**Requirements**: INFRA-03, INFRA-04, INFRA-05

**Success Criteria** (what must be TRUE):
1. `docker compose up` starts all services (frontend via Nginx, backend via Uvicorn) and the dashboard is accessible at the VPS IP/domain
2. Nginx routes API requests and WebSocket connections to the FastAPI backend, and serves the React frontend for all other routes
3. ML model inference works inside the Docker container using CPU-only PyTorch (no GPU/MPS dependency)

**Plans**: TBD

## Progress

**Execution Order:** Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation & Auth | 0/? | Not started | - |
| 2. Trading Engine & API | 0/? | Not started | - |
| 3. Dashboard UI | 0/? | Not started | - |
| 4. Docker Deployment | 0/? | Not started | - |
