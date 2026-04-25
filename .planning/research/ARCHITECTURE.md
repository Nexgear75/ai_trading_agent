# Architecture Patterns

**Domain:** AI-Powered Crypto Paper Trading Dashboard  
**Researched:** 2026-04-25

## Recommended Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     BROWSER (React)                      │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐  ┌────────┐ │
│  │  Chart    │  │ Positions│  │  Event    │  │Metrics │ │
│  │  (LWC v5) │  │  Table   │  │   Log     │  │  Bar   │ │
│  └────┬─────┘  └────┬─────┘  └─────┬─────┘  └───┬────┘ │
│       │              │              │             │       │
│  ┌────▼──────────────▼──────────────▼─────────────▼────┐ │
│  │              Zustand Store (client state)            │ │
│  │  - connection status  - selected symbol              │ │
│  │  - event log buffer   - UI preferences              │ │
│  └────┬──────────────────────────────────────┬─────────┘ │
│       │ REST (react-query)                   │ WS        │
└───────┼──────────────────────────────────────┼───────────┘
        │                                      │
   ┌────▼──────────────────────────────────────▼────┐
   │              FastAPI Backend                     │
   │                                                  │
   │  ┌──────────────┐  ┌─────────────────────────┐ │
   │  │  REST API     │  │  WebSocket Manager      │ │
   │  │  /api/status  │  │  - push events to all   │ │
   │  │  /api/start   │  │    connected browsers   │ │
   │  │  /api/stop    │  │  - heartbeat/ping       │ │
   │  │  /api/history │  │  - reconnect handling   │ │
   │  │  /api/config  │  └──────────┬──────────────┘ │
   │  └───────┬──────┘              │                 │
   │          │                     │                 │
   │  ┌───────▼─────────────────────▼──────────────┐  │
   │  │         Trading Engine Service              │  │
   │  │  - Wraps RealtimeTrading from existing code │  │
   │  │  - Emits events to WebSocket Manager        │  │
   │  │  - Receives commands from REST API          │  │
   │  │  ┌──────────────────────────────────┐       │  │
   │  │  │  Binance WebSocket (ccxt)        │       │  │
   │  │  │  - kline stream for live prices   │       │  │
   │  │  │  - reconnection with backoff      │       │  │
   │  │  └──────────────────────────────────┘       │  │
   │  └──────────────────────────────────────────┘  │
   │          │                                       │
   │  ┌───────▼──────────────────────────────────┐   │
   │  │         SQLite Database                    │   │
   │  │  - positions (open + closed)              │   │
   │  │  - trades (history)                       │   │
   │  │  - bot_config (per-symbol settings)       │   │
   │  │  - bot_state (running, circuit breaker)   │   │
   │  └──────────────────────────────────────────┘   │
   └──────────────────────────────────────────────────┘
        │
        │  Frontend also calls Binance directly:
   ┌────▼────────────────────────────────────┐
   │     Binance REST API (from browser)     │
   │     - GET /api/v3/klines (candle data)  │
   │     - GET /api/v3/ticker/price          │
   └─────────────────────────────────────────┘
```

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| **React Frontend** | UI rendering, user interaction, chart visualization | FastAPI (REST + WS), Binance (REST for chart data) |
| **FastAPI REST Layer** | CRUD operations, bot control commands, historical data queries | Trading Engine Service, SQLite, Browser |
| **FastAPI WebSocket Manager** | Push real-time events to connected browsers, handle reconnection | Trading Engine Service, Browser |
| **Trading Engine Service** | Run trading loop, execute model inference, manage positions, emit events | Binance WebSocket, WebSocket Manager, SQLite |
| **SQLite Database** | Persistent storage for positions, trades, config, bot state | Trading Engine Service, REST Layer |
| **Binance WebSocket (ccxt)** | Stream live kline data for the active symbol | Trading Engine Service |
| **Binance REST API (direct)** | Historical candle data for chart rendering | React Frontend (direct calls) |
| **Supabase Auth** | User authentication, JWT validation | React Frontend (login), FastAPI (JWT verification) |

### Data Flow

**Live trading flow:**
1. Binance WebSocket → kline event → Trading Engine
2. Trading Engine → model inference → prediction
3. If prediction exceeds threshold → open position → emit ORDER_OPENED event
4. ORDER_OPENED → WebSocket Manager → browser → update positions table + add chart marker
5. Periodic: current price → check SL/TP → close position → emit ORDER_CLOSED event
6. ORDER_CLOSED → WebSocket Manager → browser → update trades table + add exit marker on chart

**Chart data flow:**
1. Browser → Binance REST API → fetch 500 historical candles → render candlestick chart
2. Browser → Binance WebSocket (via ccxt or direct) → live candle updates → update chart
3. Backend WebSocket → prediction/trade events → add markers/lines on chart

**Bot control flow:**
1. User clicks "Start" → REST POST /api/start → Trading Engine starts loop
2. User clicks "Stop" → REST POST /api/stop → Trading Engine gracefully stops
3. Status changes → WebSocket push → browser updates connection indicator

## Patterns to Follow

### Pattern 1: Event-Driven Trading Engine

**What:** The trading engine emits typed events (KLINE, PREDICTION, ORDER_OPENED, ORDER_CLOSED, CIRCUIT_BREAKER, REBALANCE) that the WebSocket manager broadcasts to all connected clients.

**When:** Always. Every state change in the trading loop should produce an event.

**Example:**
```python
# backend/events.py
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

class EventType(str, Enum):
    KLINE = "KLINE"
    PREDICTION = "PREDICTION"
    ORDER_OPENED = "ORDER_OPENED"
    ORDER_CLOSED = "ORDER_CLOSED"
    CIRCUIT_BREAKER = "CIRCUIT_BREAKER"
    REBALANCE = "REBALANCE"
    STATUS_CHANGE = "STATUS_CHANGE"

@dataclass
class TradingEvent:
    type: EventType
    timestamp: datetime
    data: dict  # type-specific payload
```

### Pattern 2: Single Source of Truth (SQLite, not JSON)

**What:** Replace the current `state_{SYMBOL}.json` persistence with SQLite. The database is the single source of truth for positions, trades, config, and bot state.

**When:** All state reads/writes go through SQLite. No in-memory-only state that isn't also persisted.

**Example:**
```python
# backend/database.py
import aiosqlite

async def get_open_positions(db: aiosqlite.Connection, symbol: str) -> list[dict]:
    cursor = await db.execute(
        "SELECT * FROM positions WHERE symbol = ? AND status = 'OPEN'",
        (symbol,)
    )
    return await cursor.fetchall()
```

### Pattern 3: Frontend Owns Chart Data

**What:** The frontend fetches candlestick data directly from Binance REST API (no backend proxy). The backend only pushes trading events (predictions, orders, status changes). This reduces backend load and eliminates a latency hop.

**When:** Chart historical data and live candle updates. Never for trading events or bot state.

**Example:**
```typescript
// frontend/services/binance.ts
export async function fetchCandles(symbol: string, interval: string, limit = 500) {
  const url = `https://api.binance.com/api/v3/klines?symbol=${symbol.replace('/', '')}&interval=${interval}&limit=${limit}`;
  const res = await fetch(url);
  return res.json();
}
```

### Pattern 4: WebSocket Reconnection with Backoff

**What:** The frontend WebSocket client handles disconnections gracefully with exponential backoff. Shows connection status indicator. Buffers events during brief disconnections.

**When:** Always. Network interruptions are expected on VPS deployments.

**Example:**
```typescript
// frontend/hooks/useTradingWebSocket.ts
function connect(url: string, onMessage: (event: TradingEvent) => void) {
  let retryDelay = 1000;
  const maxDelay = 30000;

  function connectInner() {
    const ws = new WebSocket(url);
    ws.onclose = () => {
      setTimeout(connectInner, retryDelay);
      retryDelay = Math.min(retryDelay * 2, maxDelay);
    };
    ws.onopen = () => { retryDelay = 1000; };
    ws.onmessage = (e) => onMessage(JSON.parse(e.data));
  }
  connectInner();
}
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Backend Proxying Chart Data

**What:** Routing all Binance API calls through the FastAPI backend.  
**Why bad:** Adds latency (browser → backend → Binance → backend → browser), doubles bandwidth, and creates an unnecessary bottleneck.  
**Instead:** Frontend calls Binance REST API directly. Backend only handles trading events and bot state.

### Anti-Pattern 2: Polling for Real-Time Data

**What:** Using `setInterval` + REST polling to check for new trades or price updates.  
**Why bad:** Latency (1-30s delay), wasted bandwidth, server load. Trading events need sub-second delivery.  
**Instead:** WebSocket push from backend. REST for historical/initial data only.

### Anti-Pattern 3: God Object Trading Engine

**What:** Keeping the existing `RealtimeTrading` class as-is with all responsibilities (trading logic + UI rendering + state persistence + Binance streaming).  
**Why bad:** Can't test trading logic without Rich, can't render in browser without rewriting, can't change state persistence without touching trading code.  
**Instead:** Extract trading logic into a service class. Emit events. Let the WebSocket manager and REST layer handle presentation concerns.

### Anti-Pattern 4: Shared Mutable State Between Threads

**What:** The current code uses `threading.Lock` and shared `RealtimeState` between the Binance stream thread and the main loop.  
**Why bad:** In FastAPI's async context, mixing threading locks with asyncio is fragile. Deadlocks are easy to introduce.  
**Instead:** Use `asyncio.Queue` for event passing between the Binance stream thread and the async trading loop. The stream thread puts events on the queue; the async loop consumes them.

### Anti-Pattern 5: SQLite Without WAL Mode

**What:** Using SQLite's default journal mode for a system that reads and writes concurrently.  
**Why bad:** Default journal mode locks the entire database during writes, blocking reads. With a WebSocket pushing events every second, reads will stall.  
**Instead:** Enable WAL mode (`PRAGMA journal_mode=WAL;`) for concurrent read/write access.

## Scalability Considerations

| Concern | At 1 user (v1) | At 10 users | At 100 users |
|---------|----------------|-------------|--------------|
| WebSocket connections | 1-2 browser tabs | 10-20 connections | Need connection pooling, separate WS server |
| SQLite write throughput | ~100 writes/sec (WAL mode) | Still fine for single bot | Need PostgreSQL migration |
| Binance API rate limits | 1200 req/min (REST) | Same — frontend calls directly | Need backend proxy with caching |
| Model inference | <100ms per candle (CPU) | Same — single bot instance | Need GPU inference or model serving |
| Docker resources | 512MB RAM, 1 CPU | 1GB RAM, 2 CPU | Need horizontal scaling, load balancer |

**v1 is single-user, single-bot, single-symbol.** All scalability concerns beyond 1 user are deferred. Architecture must not prevent future scaling, but no optimization needed now.

## Sources

- Existing codebase: `testing/realtime_testing.py` (RealtimeTrading class, ConnectionState, event logging, threading model)
- FastAPI WebSocket docs: https://fastapi.tiangolo.com/advanced/websockets/
- SQLite WAL mode: https://www.sqlite.org/wal.html
- Lightweight Charts: https://tradingview.github.io/lightweight-charts/
- Freqtrade architecture: Vue.js frontend + Python backend + WebSocket, similar pattern
