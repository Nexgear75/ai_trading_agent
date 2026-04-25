# Requirements: AI Trading Bot Dashboard

**Defined:** 2026-04-25
**Core Value:** The bot executes trades reliably and the dashboard shows exactly what it's doing — positions, PnL, and model predictions live on the chart.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Infrastructure

- [ ] **INFRA-01**: SQLite database with tables for bot_state, positions, trades, and portfolio_snapshots (WAL mode enabled for concurrent reads)
- [ ] **INFRA-02**: Database migrations managed via Alembic with auto-generated revision scripts
- [ ] **INFRA-03**: Docker Compose configuration with separate frontend, backend, and Nginx reverse proxy containers
- [ ] **INFRA-04**: Nginx reverse proxy routes API and WebSocket requests to FastAPI backend
- [ ] **INFRA-05**: CPU-only PyTorch Docker image for ML model inference (reduced image size)

### Backend — Trading Engine

- [ ] **ENGN-01**: Async trading engine ported from existing `realtime_testing.py` using asyncio (replacing threading + queue.Queue)
- [ ] **ENGN-02**: PyTorch model inference runs in thread executor via `asyncio.to_thread()` to avoid blocking event loop
- [ ] **ENGN-03**: Binance WebSocket kline stream uses async connection with automatic reconnection on disconnect
- [ ] **ENGN-04**: Trading engine persists state mutations (position open/close, capital update) to SQLite on every change
- [ ] **ENGN-05**: Paper trading simulation includes realistic slippage, Maker/Taker fees, and RRR-based Stop-Loss/Take-Profit
- [ ] **ENGN-06**: Circuit breaker and risk management logic (max drawdown, cooldown, daily trade limits) carried over from existing implementation
- [ ] **ENGN-07**: Trading engine runs independently of browser WebSocket connections (engine stays alive even if no clients connected)

### Backend — API Layer

- [ ] **API-01**: FastAPI application with REST endpoints for bot lifecycle (start, stop, restart, status)
- [ ] **API-02**: REST endpoint returns open positions list with entry price, SL, TP, direction, unrealized PnL
- [ ] **API-03**: REST endpoint returns closed trades history with entry/exit dates, prices, net PnL, fees, exit reason
- [ ] **API-04**: REST endpoint returns portfolio metrics (capital, allocated, portfolio value, PnL, win rate)
- [ ] **API-05**: WebSocket endpoint pushes real-time bot events to connected clients (ORDER_OPENED, ORDER_CLOSED, CANDLE_CLOSED, PREDICTION, CIRCUIT_BREAKER, STATE_SNAPSHOT)
- [ ] **API-06**: WebSocket sends full STATE_SNAPSHOT on client connection/reconnection for immediate UI hydration
- [ ] **API-07**: Supabase JWT verification on all API and WebSocket endpoints using PyJWT with JWKS key rotation

### Frontend — Authentication

- [ ] **AUTH-01**: User can log in via Supabase Auth PKCE flow (email/password)
- [ ] **AUTH-02**: Dashboard routes are protected — unauthenticated users redirect to login page
- [ ] **AUTH-03**: User session persists across browser refreshes via Supabase session management
- [ ] **AUTH-04**: User can log out from any page in the dashboard

### Frontend — Chart & Visualization

- [ ] **CHRT-01**: Candlestick chart rendered with TradingView Lightweight Charts v5 (custom `useLightweightChart` React hook, NOT the abandoned npm wrapper)
- [ ] **CHRT-02**: Chart loads historical candles from Binance REST API on mount
- [ ] **CHRT-03**: Chart updates in real-time with new candles via backend WebSocket events
- [ ] **CHRT-04**: Trade markers displayed on chart (arrow-up for BUY, arrow-down for SELL, color-coded by direction)
- [ ] **CHRT-05**: Stop-Loss and Take-Profit price lines rendered on chart for open positions (red for SL, green for TP)
- [ ] **CHRT-06**: Dark theme applied to chart matching dashboard overall dark theme

### Frontend — Dashboard Controls

- [ ] **CTRL-01**: Start/Stop/Restart buttons control trading engine lifecycle with optimistic UI updates
- [ ] **CTRL-02**: Crypto selector dropdown switches active trading symbol (stops current bot, starts new one)
- [ ] **CTRL-03**: Binance connection status indicator (ONLINE green, RECONNECTING yellow, OFFLINE red)
- [ ] **CTRL-04**: Bot status indicator shows current engine state (RUNNING, STOPPED, ERROR)

### Frontend — Data Display

- [ ] **DATA-01**: Open positions table shows direction, entry price, SL, TP, unrealized PnL, allocated capital
- [ ] **DATA-02**: Closed trades history table shows entry/exit dates, prices, net PnL, fees, exit reason (TP/SL/EXPIRATION)
- [ ] **DATA-03**: Portfolio metrics cards display capital, allocated capital, portfolio value, total PnL, win rate
- [ ] **DATA-04**: Trade execution timeline shows chronological event log (CANDLE_CLOSED, PREDICTION, ORDER_OPENED, ORDER_CLOSED) color-coded by type

### Frontend — Theming

- [ ] **THEME-01**: Dark theme applied across entire dashboard using TailwindCSS dark variant
- [ ] **THEME-02**: Responsive layout optimized for 1280px+ viewport (desktop-first, not broken on smaller screens)

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Advanced Visualization

- **VIZ-01**: Model prediction visualization on chart (predicted return % near trade markers or tooltip)
- **VIZ-02**: Equity curve — portfolio value over time on secondary chart pane
- **VIZ-03**: Drawdown visualization as gauge or progress bar with warning colors at thresholds

### Advanced Controls

- **CTRL-05**: Configurable risk parameters from UI (RRR, threshold, max drawdown, cooldown) without restarting
- **CTRL-06**: Risk management status panel showing circuit breaker state, cooldown countdown, daily trade count

### Multi-Asset

- **MULTI-01**: Support for simultaneous multi-crypto trading with per-symbol engine instances
- **MULTI-02**: Portfolio-level aggregation across multiple trading pairs

### Live Trading

- **LIVE-01**: Live trading mode with real Binance API keys (requires safety audit)
- **LIVE-02**: Order execution confirmation flow before placing real orders

### Notifications

- **NOTF-01**: Push notifications via Telegram when positions open/close
- **NOTF-02**: Push notifications via Discord webhook for trade events

## Out of Scope

| Feature | Reason |
|---------|--------|
| Model retraining from dashboard | Training is compute-intensive, blocks event loop; CLI already handles this |
| Backtesting from dashboard | `testing/backtesting.py` already works from CLI; web backtesting needs separate compute pipeline |
| Technical indicators overlay (RSI, MACD) | The bot uses ML predictions, not indicators; users can use TradingView for technical analysis |
| Social features (sharing, leaderboards) | Single-user tool, no social context |
| Mobile-responsive design | Dashboard is for desktop monitoring; real-time charting requires large screen |
| OAuth login (Google, GitHub) | Email/password sufficient for v1 |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| INFRA-01 | Phase 1 | Pending |
| INFRA-02 | Phase 1 | Pending |
| AUTH-01 | Phase 1 | Pending |
| AUTH-02 | Phase 1 | Pending |
| AUTH-03 | Phase 1 | Pending |
| AUTH-04 | Phase 1 | Pending |
| ENGN-01 | Phase 2 | Pending |
| ENGN-02 | Phase 2 | Pending |
| ENGN-03 | Phase 2 | Pending |
| ENGN-04 | Phase 2 | Pending |
| ENGN-05 | Phase 2 | Pending |
| ENGN-06 | Phase 2 | Pending |
| ENGN-07 | Phase 2 | Pending |
| API-01 | Phase 2 | Pending |
| API-02 | Phase 2 | Pending |
| API-03 | Phase 2 | Pending |
| API-04 | Phase 2 | Pending |
| API-05 | Phase 2 | Pending |
| API-06 | Phase 2 | Pending |
| API-07 | Phase 2 | Pending |
| CHRT-01 | Phase 3 | Pending |
| CHRT-02 | Phase 3 | Pending |
| CHRT-03 | Phase 3 | Pending |
| CHRT-04 | Phase 3 | Pending |
| CHRT-05 | Phase 3 | Pending |
| CHRT-06 | Phase 3 | Pending |
| CTRL-01 | Phase 3 | Pending |
| CTRL-02 | Phase 3 | Pending |
| CTRL-03 | Phase 3 | Pending |
| CTRL-04 | Phase 3 | Pending |
| DATA-01 | Phase 3 | Pending |
| DATA-02 | Phase 3 | Pending |
| DATA-03 | Phase 3 | Pending |
| DATA-04 | Phase 3 | Pending |
| THEME-01 | Phase 3 | Pending |
| THEME-02 | Phase 3 | Pending |
| INFRA-03 | Phase 4 | Pending |
| INFRA-04 | Phase 4 | Pending |
| INFRA-05 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 30 total
- Mapped to phases: 30
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-25*
*Last updated: 2026-04-25 after initial definition*
