# Feature Landscape

**Domain:** Crypto trading bot dashboard — real-time paper trading visualization
**Researched:** 2026-04-25

## Table Stakes

Features users expect. Missing = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Candlestick chart with real-time updates** | Core visualization for any trading UI. Without it, the dashboard is just numbers. | Medium | Binance REST → Lightweight Charts. `setData()` for history, `update()` for incremental. |
| **Trade markers on chart** | Shows exactly when the bot bought/sold. Core value proposition. | Medium | `SeriesMarkersPrimitive` — arrowUp (BUY), arrowDown (SELL). Color by direction. |
| **Open positions table** | Users need to see what the bot is currently holding. | Low | Table: direction, entry price, SL, TP, unrealized PnL, allocated capital. |
| **Closed trades history** | Review past decisions. Essential for learning what the model does. | Low | Scrollable table: entry/exit dates, prices, PnL, fees, exit reason (TP/SL/EXPIRATION). |
| **Portfolio metrics** | At-a-glance health: capital, allocated, portfolio value, PnL, win rate. | Low | Real-time computed from positions + trades. Matches existing `DashboardView` metrics. |
| **Start/Stop/Restart controls** | User must be able to control the bot lifecycle. | Medium | REST endpoints → Trading Engine lifecycle. Optimistic UI + WS reconciliation. |
| **Crypto selector** | Switch between BTC, ETH, SOL, etc. | Low | Dropdown from `SYMBOLS` in `config.py`. Stops current bot, starts new one for selected symbol. |
| **Login / Auth protection** | No unauthenticated access. Supabase PKCE flow. | Medium | Auth context provider, route guard, login page. JWT validation on backend. |
| **Dark theme** | Financial dashboards are universally dark-themed. | Low | TailwindCSS `dark:` variant. Lightweight Charts dark theme preset. |
| **SL/TP price lines on chart** | Visual representation of where positions will close. | Medium | `createPriceLine()` on Lightweight Charts series. Green for TP, red for SL. |
| **Binance connection status** | Users need to know if the bot is receiving live data. | Low | Status indicator: ONLINE (green), RECONNECTING (yellow), OFFLINE (red). From `ConnectionState`. |

## Differentiators

Features that set product apart. Not expected, but valued.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Model prediction visualization** | Shows *why* the bot opened a position. Predicted return % displayed on chart or tooltip. | Medium | `PREDICTION` event → show predicted return near trade marker. Tooltip or inline label. |
| **Risk management status panel** | Makes risk controls visible: circuit breaker state, cooldown countdown, daily trade count. | Low | Cards/indicators showing current risk state. Prevents user confusion when bot "stops trading". |
| **Equity curve** | Portfolio value over time. Visual proof of strategy performance. | Medium | `portfolio_snapshots` table → line series on secondary chart pane. Cumulative PnL visualization. |
| **Configurable risk parameters from UI** | Change RRR, threshold, max drawdown, cooldown without restarting. | Medium | REST endpoints to update `bot_config` + `risk_state`. Restart required for some changes (model, timeframe). |
| **Trade execution timeline** | Chronological event log (matches existing terminal dashboard log). | Low | Scrollable event list: CANDLE_CLOSED, PREDICTION, ORDER_OPENED, ORDER_CLOSED, CIRCUIT_BREAKER. Color-coded. |
| **Drawdown visualization** | Current drawdown % as gauge or progress bar. Warning colors at thresholds. | Low | Computed from peak portfolio value. Red at >15%, yellow at >10%. |

## Anti-Features

Features to explicitly NOT build.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Live trading with real money** | Safety-critical. A bug could lose real funds. | Paper trading only in v1. Architecture must not prevent live trading in v2, but don't implement it. |
| **Model retraining from dashboard** | Training is compute-intensive, blocks event loop, separate concern. | CLI only (`python -m models.cnn.training`). Dashboard does inference only. |
| **Multi-asset simultaneous trading** | Significant architecture complexity (per-symbol engines, resource management). | Single asset at a time in v1. `SYMBOLS` selector switches the active bot. |
| **Push notifications (Telegram/Discord)** | Not core value. Adds dependency on external services. | Deferred to v2. The event log on dashboard is sufficient for v1. |
| **Backtesting from the dashboard** | `testing/backtesting.py` already works from CLI. Web backtesting would need separate compute pipeline. | CLI only. Dashboard is for live/paper trading monitoring. |
| **Technical indicators overlay on chart** | Lightweight Charts supports it but it's scope creep. The bot doesn't use indicators for decisions — it uses ML predictions. | Show model predictions instead. If users want RSI/MACD, they can use TradingView. |
| **Social features (sharing, leaderboards)** | Single-user tool. No social context. | N/A |
| **Mobile-responsive design** | Dashboard is for desktop monitoring. Real-time charting requires large screen. | Focus on 1280px+ viewport. Ensure it doesn't break on smaller screens, but don't optimize for mobile. |

## Feature Dependencies

```
Login/Auth → Dashboard access (everything depends on auth)
Candlestick chart → Trade markers (markers overlay on chart)
Candlestick chart → SL/TP price lines (price lines on same series)
Open positions → SL/TP price lines (positions define the lines)
Start/Stop controls → Trading Engine lifecycle
Crypto selector → Bot restart (switching asset = stop + start)
Closed trades → Equity curve (equity curve derived from trade PnL + snapshots)
Portfolio metrics ← Open positions + Closed trades (computed from both)
Risk management panel ← Trading Engine risk state (read-only view)
Trade execution timeline ← WebSocket events (all events flow through timeline)
```

## MVP Recommendation

Prioritize:
1. **Candlestick chart with trade markers** — core value: see what the bot is doing
2. **Start/Stop/Restart controls** — must be able to control the bot
3. **Portfolio metrics + open positions** — know the bot's state at a glance
4. **Auth protection** — no unauthenticated access

Defer:
- **Equity curve**: Requires `portfolio_snapshots` accumulation over time. Can add after v1 ships — no historical data exists yet.
- **Configurable risk parameters from UI**: Changing config mid-run adds edge cases. Start with config file, add UI controls later.
- **Model prediction visualization**: Nice-to-have. The trade markers already show the bot's decisions.

## Feature Inventory from Existing Codebase

The existing `realtime_testing.py` already implements these features in the terminal UI. The dashboard ports them to the web:

| Existing Feature (Terminal) | Dashboard Equivalent | Status |
|------------------------------|---------------------|--------|
| `DashboardView._render_status_bar()` | Connection status indicator + bot status | Port needed |
| `DashboardView._render_body()` → positions table | Open positions table | Port needed |
| `DashboardView._render_body()` → metrics panel | Portfolio metrics cards | Port needed |
| `DashboardView._render_log()` → event log | Trade execution timeline | Port needed |
| `print_summary()` → equity curve, win/loss stats | Equity curve + metrics | Port needed |
| `RealtimePosition` dataclass | `open_positions` table + API | Port needed |
| `RealtimeTrade` dataclass | `closed_trades` table + API | Port needed |
| `ConnectionState` + `ConnStatus` | WebSocket status indicator | Port needed |
| Circuit breaker logic | Risk management status panel | Port needed |
| `_save_state()` / `_load_state()` (JSON) | SQLite State Manager | Rewrite needed |
| `BinanceKlineStream` (threading) | Async Binance WS stream | Rewrite needed |
| `RealtimeTester.run()` (event loop) | `TradingEngine.run()` (async) | Rewrite needed |
| `predict_return()` (manual model + scaler load) | `registry.get_predictor()` + `BasePredictor` | Refactor to use existing registry |

## Sources

- Existing `testing/realtime_testing.py`: Feature inventory (HIGH confidence, primary source)
- Existing `testing/config.json`: Risk management parameters (HIGH confidence)
- PROJECT.md requirements: Active requirements list (HIGH confidence)
- TradingView Lightweight Charts docs: Chart features (HIGH confidence, official)
- Supabase Auth React docs: Auth flow features (HIGH confidence, official)
