# Technology Stack

**Project:** AI Trading Bot Dashboard  
**Researched:** 2026-04-25

## Recommended Stack

All decisions pre-validated in PROJECT.md. This document confirms the choices and provides rationale.

### Core Framework (Frontend)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| React | 19.x | UI framework | Largest ecosystem, best component library support, team familiarity. Needed for real-time dashboard with frequent re-renders. |
| Vite | 6.x | Build tool / dev server | Fastest HMR, native ESM, excellent React plugin. Essential for rapid iteration on chart components. |
| TailwindCSS | 4.x | Utility-first CSS | Rapid styling without context-switching to CSS files. Dark theme support built-in. Consistent spacing/sizing tokens. |
| TypeScript | 5.x | Type safety | Catches API contract mismatches between frontend and backend. Essential for WebSocket message type safety. |

### Chart Library

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Lightweight Charts | 5.x | Candlestick chart rendering | TradingView's open-source library. ~40KB bundle. Purpose-built for financial charts. Native candlestick, volume, and marker support. v5 adds pane support for multiple sub-charts. |

### Database

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| SQLite | 3.x | Bot state, positions, trades, config | Simpler VPS deployment than PostgreSQL. Single-file database, no external service. Adequate for single-user paper trading. Python stdlib `sqlite3` + async wrapper. |

### Backend

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| FastAPI | 0.115+ | REST API + WebSocket server | Native async support, auto-generated OpenAPI docs, built-in WebSocket via `WebSocket` class. Decided over Flask in PROJECT.md for native async + WebSocket. |
| Uvicorn | 0.34+ | ASGI server | Standard FastAPI runner. Supports WebSocket natively. |
| Pydantic | 2.x | Request/response validation | FastAPI's native serialization. Type-safe API contracts matching frontend TypeScript types. |
| ccxt | 4.x | Binance API client | Already used in existing codebase for market data fetching. Maintains consistency. |
| joblib | 1.x | Model scaler persistence | Already used in existing codebase for saving/loading scalers alongside model checkpoints. |

### Authentication

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Supabase Auth | — | Managed authentication | No custom auth logic. Email/password signup. JWT tokens. Free tier sufficient for single-user. Decided in PROJECT.md. |
| @supabase/supabase-js | 2.x | Frontend auth client | Official Supabase JS client. Handles login, session management, token refresh. |
| python-jose | 3.x | Backend JWT validation | Verify Supabase JWTs in FastAPI middleware. Lightweight, no external service dependency. |

### Infrastructure

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Docker | — | Containerization | Reproducible deployment. Single `docker compose up` on VPS. Decided in PROJECT.md. |
| Docker Compose | — | Multi-container orchestration | Frontend container (nginx serving built React) + backend container (FastAPI + uvicorn) + optional SQLite volume. |
| Nginx | — | Frontend static serving + reverse proxy | Serve built React assets. Proxy `/api/` and `/ws/` to FastAPI backend. SSL termination. |

### Supporting Libraries (Frontend)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| tanstack/react-query | 5.x | Server state management | Fetching REST data (positions, trades, metrics) with caching, refetching, and stale-while-revalidate. |
| zustand | 5.x | Client state management | WebSocket connection state, UI state (selected symbol, dashboard layout preferences). Lightweight alternative to Redux. |
| date-fns | 4.x | Date formatting | Timestamp formatting in event log and trade tables. Tree-shakeable, smaller than moment.js. |

### Supporting Libraries (Backend)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| aiosqlite | 0.21+ | Async SQLite access | Non-blocking database queries in FastAPI async handlers. |
| websockets | 14.x | WebSocket protocol | FastAPI uses this under the hood. Direct usage only if custom WebSocket handling needed. |

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Frontend framework | React | Svelte / Vue | Svelte: smaller ecosystem for chart integrations. Vue: Freqtrade uses it but React has broader component library. PROJECT.md decided React. |
| Chart library | Lightweight Charts | Chart.js / D3.js / Recharts / TradingView Widget | Chart.js: not financial-chart native. D3: too low-level, 10x dev time. Recharts: no candlestick support. TradingView Widget: requires hosting, not open-source. Lightweight Charts is purpose-built and free. |
| Database | SQLite | PostgreSQL | PostgreSQL: overkill for single-user paper trading on a VPS. Requires separate service, connection pooling, backups. SQLite is sufficient and simpler. |
| Auth | Supabase Auth | Auth0 / custom JWT | Auth0: free tier limited, vendor lock-in. Custom JWT: reinventing the wheel, security risk. Supabase: managed, free tier, no custom auth code. |
| Build tool | Vite | Webpack / Next.js | Webpack: slower, more config. Next.js: SSR framework overkill for a single-page dashboard. Vite: fastest DX, simplest config. |
| CSS framework | TailwindCSS | CSS Modules / styled-components / shadcn | CSS Modules: no utility system, slower iteration. styled-components: runtime overhead. shadcn: component library (can use alongside TailwindCSS later). |
| Backend framework | FastAPI | Flask / Django | Flask: no native async/WebSocket. Django: monolithic, overkill for API-only backend. FastAPI: async-native, WebSocket support, auto-docs. |
| State management | zustand | Redux Toolkit / Jotai | Redux: boilerplate overkill for this scope. Jotai: too atomic, harder for WebSocket state. zustand: minimal API, good for real-time state. |

## Installation

```bash
# Frontend (from dashboard/ directory)
npm create vite@latest . -- --template react-ts
npm install lightweight-charts @supabase/supabase-js @tanstack/react-query zustand date-fns
npm install -D tailwindcss @tailwindcss/vite

# Backend (from api/ directory, Python 3.11+)
pip install fastapi uvicorn[standard] aiosqlite python-jose[cryptography] ccxt pydantic

# Existing codebase dependencies (already installed)
pip install -r requirements.txt  # torch, ccxt, pandas, scikit-learn, joblib, etc.
```

## Sources

- PROJECT.md: All tech stack decisions pre-validated
- Lightweight Charts v5: https://tradingview.github.io/lightweight-charts/ — confirmed candlestick, markers, and pane support
- FastAPI WebSocket docs: https://fastapi.tiangolo.com/advanced/websockets/ — native WebSocket class
- Supabase Auth docs: https://supabase.com/docs/guides/auth — JWT validation flow verified
- Competitive analysis: Freqtrade uses Vue + PrimeVue; 3Commas uses proprietary stack; Hummingbot is CLI-first
