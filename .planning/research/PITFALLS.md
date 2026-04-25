# Domain Pitfalls

**Domain:** Crypto trading bot dashboard — real-time paper trading visualization
**Researched:** 2026-04-25

## Critical Pitfalls

Mistakes that cause rewrites or major issues.

### Pitfall 1: Blocking the Async Event Loop with Model Inference

**What goes wrong:** Running `model.predict()` synchronously inside the FastAPI event loop blocks all WebSocket broadcasts, API responses, and other async tasks while inference runs.

**Why it happens:** PyTorch inference is CPU-bound (or MPS-bound on Apple Silicon). A CNN-BiLSTM-AM forward pass takes ~5-50ms on CPU, which blocks the event loop for that duration. On a 1d timeframe this is tolerable (once/day), but on 1h or shorter timeframes, the blocking becomes noticeable.

**Consequences:** WebSocket events queue up during inference → delayed ORDER_OPENED/CLOSED delivery → stale dashboard → user sees positions update seconds after they open.

**Prevention:** Run inference in a `ThreadPoolExecutor` or `asyncio.to_thread()`. The model is not thread-safe for concurrent calls (PyTorch `model.eval()` is OK for single-threaded inference), so use a semaphore if multiple inference calls could overlap.

```python
# CORRECT: Offload to thread pool
async def _on_candle_closed(self, event: KlineEvent):
    prediction = await asyncio.to_thread(self.model.predict, market_window)
    # ... process prediction
```

**Detection:** If WebSocket broadcast latency exceeds 100ms consistently during candle close events, the event loop is blocked.

### Pitfall 2: Race Condition Between Binance WS Reconnect and State Recovery

**What goes wrong:** On Binance WebSocket reconnection, the stream resumes from the latest candle. But if positions were opened/closed during the disconnected period, the in-memory `df_history` is stale and the system may make decisions on outdated data.

**Why it happens:** The existing `BinanceKlineStream` handles reconnection by re-subscribing to the WS stream. But it doesn't automatically re-fetch the history that was missed. The current `_refetch_history_after_reconnect()` does a REST fetch, but there's a time gap between reconnect and history rebuild where the engine could process a stale candle.

**Consequences:** Model predicts on stale features → bad trade decisions → phantom positions or missed exits.

**Prevention:**
1. Pause the trading engine (stop processing events) immediately on WS disconnect.
2. On reconnect: fetch missing history via REST → rebuild `df_history` → check all open positions against current price (SL/TP may have been hit during downtime) → resume engine.
3. Only then re-subscribe to the WS stream.

```python
async def _on_reconnect(self, event: ReconnectEvent):
    self.engine_paused = True
    await self._refetch_history()
    await self._check_positions_against_current_price()  # SL/TP may have triggered
    self.engine_paused = False
```

**Detection:** Log the duration of WS disconnections. If >1 timeframe period (e.g., >1 day for 1d), flag for manual review.

### Pitfall 3: SQLite Write-Ahead Lock Under Concurrent Access

**What goes wrong:** SQLite in WAL mode allows concurrent reads but still serializes writes. If the trading engine writes position state on every mutation AND the REST API reads state for frontend requests, long-running read queries can delay write commits.

**Why it happens:** WAL mode helps, but a long `SELECT` on `closed_trades` (e.g., fetching 10K rows for trade history) can delay a `UPDATE` on `open_positions` (e.g., closing a position). The write waits for the read transaction to complete.

**Consequences:** Position closure delayed by milliseconds → next candle might try to open a new position before the old one is properly closed → double position error.

**Prevention:**
1. Keep read queries fast: add indexes on `closed_trades(symbol, exit_date)`, `open_positions(symbol)`.
2. Use `PRAGMA journal_mode=WAL` and `PRAGMA synchronous=NORMAL` (not FULL — acceptable for paper trading, not for financial records).
3. Keep write transactions short: don't compute metrics inside a write transaction.
4. Separate read and write connection pools if needed (aiosqlite handles this).

**Detection:** Enable `PRAGMA busy_timeout=5000` — if any query waits >1s, log a warning.

### Pitfall 4: Frontend WebSocket Disconnect During Active Trade

**What goes wrong:** The browser WebSocket disconnects (network blip, laptop sleep, tab backgrounded). When it reconnects, the frontend state is stale — it doesn't know about trades that happened while disconnected.

**Why it happens:** WebSocket is a push-only channel. If the client isn't connected when an event is sent, it's lost. There's no built-in replay mechanism.

**Consequences:** User sees no open positions when there actually are some. Missing trade markers on chart. Stale metrics. User might try to start a second bot instance.

**Prevention:**
1. On WebSocket connect/reconnect, send a `STATE_SNAPSHOT` event with current full state (positions, metrics, risk state, recent trades).
2. Frontend reconciles: replaces entire local state with the snapshot.
3. Keep a small event buffer (last 100 events) on the backend for replay on reconnect.

```python
# On WS connect
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    # Send current state immediately
    snapshot = await state_manager.get_full_snapshot()
    await websocket.send_json({"event_type": "STATE_SNAPSHOT", **snapshot})
    # Then listen for new events
```

**Detection:** Frontend logs WS disconnect duration. If >5 seconds, show a "Reconnecting..." banner. On reconnect, show "State synchronized" toast.

### Pitfall 5: Binance API Rate Limiting on Frontend

**What goes wrong:** The frontend calls Binance REST API directly for candle data. If the user switches symbols rapidly (clicking through the crypto selector), each switch triggers a new `GET /api/v3/klines` request. Combined with the auto-refresh poll, this can hit Binance rate limits (1200 req/min per IP).

**Why it happens:** No debouncing on the symbol selector. Each click immediately fetches new candle history. The auto-refresh interval also continues firing.

**Consequences:** HTTP 429 from Binance → chart shows no data → dashboard appears broken.

**Prevention:**
1. Debounce the symbol selector: 500ms delay after last change before fetching.
2. Cancel in-flight Binance requests when symbol changes (use `AbortController`).
3. Cache candle data per symbol in frontend state (don't re-fetch if user switches back).
4. Pause auto-refresh when tab is not visible (`document.visibilityState`).

**Detection:** Monitor for HTTP 429 responses. Show user-facing message "Rate limited by Binance, retrying in X seconds."

## Moderate Pitfalls

### Pitfall 1: Supabase JWKS Endpoint Downtime

**What goes wrong:** Backend can't verify JWTs because `https://<project>.supabase.co/auth/v1/.well-known/jwks.json` is unreachable.

**Prevention:** Cache the JWKS response with `TTLCache(maxsize=1, ttl=86400)`. If the endpoint is down on cache expiry, continue using the cached keys for a grace period (another 24h). Log a warning. Supabase rotates keys infrequently (months), so stale cache is safe.

### Pitfall 2: Timezone Mismatches Between Binance and Dashboard

**What goes wrong:** Binance returns timestamps in UTC milliseconds. The dashboard displays times in the user's local timezone. If not handled consistently, candle times and trade entry/exit times appear misaligned.

**Prevention:** Store all timestamps as ISO 8601 UTC strings in SQLite. Convert to user's local timezone only in the frontend display layer. Use `time` in Lightweight Charts as UNIX timestamp (seconds) — it handles timezone display automatically.

### Pitfall 3: Model Checksum Mismatch

**What goes wrong:** User selects a model type (e.g., "cnn_bilstm_am") but the checkpoint file was trained with a different `config.py` (e.g., different `pool_size`, `channels`). The model loads but produces garbage predictions.

**Prevention:** Store model metadata (architecture config, timeframe, feature count) alongside the checkpoint. On `load()`, validate that the config matches the current `config.py` settings. The existing `SupervisedPredictor._n_model_features()` already handles feature count mismatch silently — add explicit validation instead.

### Pitfall 4: Docker Volume for SQLite on VPS

**What goes wrong:** SQLite database file is stored inside the container filesystem. When the container is recreated (update, crash), all trade history is lost.

**Prevention:** Mount a Docker volume for the data directory: `volumes: - ./data/db:/app/data`. The `docker-compose.yml` must explicitly define this. Document the backup procedure (`cp data/db/trading.db data/db/trading.db.backup`).

### Pitfall 5: WebSocket Message Size for Full State Snapshots

**What goes wrong:** The `STATE_SNAPSHOT` event sent on WS reconnect contains all open positions + recent closed trades + metrics. If the trade history grows large, this message can exceed browser WebSocket frame limits (~64KB default in some proxies).

**Prevention:** Limit the snapshot to essential data: current open positions + last 100 closed trades + current metrics. Full trade history is available via REST API pagination. Keep snapshot events under 10KB.

## Minor Pitfalls

### Pitfall 1: TailwindCSS Purge Excluding Dynamic Classes

**What goes wrong:** TailwindCSS purges unused CSS classes in production. Dynamic class names (e.g., `text-${color}-500`) are purged because they can't be detected statically.

**Prevention:** Use full class names, not template literals. E.g., `text-red-500` not `` `text-${status}-500` ``. Use a mapping object: `{ long: "text-green-500", short: "text-red-500" }`.

### Pitfall 2: Lightweight Charts Time Format

**What goes wrong:** Lightweight Charts expects `time` as either `'YYYY-MM-DD'` string, UNIX timestamp in seconds, or `BusinessDay` object. Binance returns timestamps in milliseconds. Passing milliseconds instead of seconds causes charts to render far-future dates.

**Prevention:** Convert Binance timestamps: `Math.floor(binanceTs / 1000)`. Use the `Time` type from Lightweight Charts for type safety.

### Pitfall 3: FastAPI WebSocket Path in Nginx

**What goes wrong:** Nginx doesn't proxy WebSocket connections by default. Requests to `/ws/trading` return 400 or get dropped.

**Prevention:** Add WebSocket headers in Nginx config:
```nginx
location /ws/ {
    proxy_pass http://backend:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}
```

### Pitfall 4: Binance Symbol Format Mismatch

**What goes wrong:** Internal config uses `"BTC/USDT"` format (ccxt). Binance REST API uses `"BTCUSDT"` format. Lightweight Charts doesn't care about format, but mixing formats causes API 404s.

**Prevention:** Normalize symbol format at API boundary. Create a utility function `to_binance_symbol("BTC/USDT") → "BTCUSDT"`. The frontend must use the Binance format when calling Binance REST, and the ccxt format when talking to the backend.

### Pitfall 5: PyTorch MPS Availability in Docker

**What goes wrong:** The model falls back to CPU in Docker (Linux VPS has no MPS). If the code assumes MPS availability, it may crash or produce different inference results.

**Prevention:** Use the existing device detection pattern: `mps if available, else cpu`. Docker container will use CPU. For a 1d timeframe (1 inference/day), CPU is fine. For 1h or faster, consider adding GPU support in v2.

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Database Layer (SQLite schema) | Missing indexes → slow queries as trade history grows | Add indexes on `closed_trades(symbol, exit_date)`, `portfolio_snapshots(timestamp)` from day 1 |
| Trading Engine (async port) | Blocking event loop with sync model inference | Use `asyncio.to_thread()` from the start. Don't "add it later." |
| Trading Engine (async port) | Race condition on WS reconnect | Pause engine on disconnect, resume only after full state recovery |
| FastAPI Backend (WebSocket) | Lost events during client disconnect | Send `STATE_SNAPSHOT` on connect/reconnect |
| FastAPI Backend (Auth) | JWKS cache miss during Supabase downtime | Cache with 24h TTL + 24h grace period |
| React Frontend (chart) | Binance rate limiting on rapid symbol switches | Debounce selector, cancel in-flight requests, cache per-symbol |
| React Frontend (chart) | Binance timestamps in ms vs Lightweight Charts seconds | Normalize at fetch boundary |
| Docker Deployment | SQLite data loss on container recreation | Mount Docker volume for DB directory |
| Docker Deployment | Nginx not proxying WebSocket | Add `Upgrade` headers in Nginx config |
| Docker Deployment | MPS not available in Linux container | Use CPU device in Docker, test inference works on CPU |

## Sources

- Existing `testing/realtime_testing.py`: Reconnect handling, state persistence, event loop patterns (HIGH confidence, primary source)
- FastAPI WebSocket docs: Connection management, disconnect handling (HIGH confidence, official)
- SQLite WAL mode docs: Concurrent access patterns (HIGH confidence, official)
- Binance API docs: Rate limits, timestamp format (HIGH confidence, official)
- Supabase Auth docs: JWKS endpoint, JWT structure (HIGH confidence, official)
- Lightweight Charts docs: Time format, SeriesMarkersPrimitive (HIGH confidence, official)
- Docker docs: Volume mounts (HIGH confidence, official)
