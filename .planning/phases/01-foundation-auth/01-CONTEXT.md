# Phase 1: Foundation & Auth - Context

**Gathered:** 2026-04-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can log in securely and all application state persists in SQLite. This phase delivers the database layer (SQLite + Alembic migrations + WAL mode) and the authentication layer (Supabase Auth PKCE flow + JWT verification middleware). No trading engine, no WebSocket, no chart — just the foundation that everything else builds on.

</domain>

<decisions>
## Implementation Decisions

### Database Schema
- **D-01:** SQLite with WAL mode enabled on connection (`PRAGMA journal_mode=WAL`, `PRAGMA synchronous=NORMAL`) for concurrent read access during WebSocket push
- **D-02:** Four core tables: `bot_state` (singleton row for engine status/config), `positions` (open trades with SL/TP/entry/direction), `trades` (closed trade history with PnL/fees/exit_reason), `portfolio_snapshots` (periodic capital snapshots for future equity curve)
- **D-03:** All timestamp columns stored as UTC ISO-8601 strings (`TEXT` type in SQLite) — consistent with Python `datetime.isoformat()` and JSON serialization
- **D-04:** Indexes from day one: `positions(symbol)`, `trades(symbol, exit_date)`, `portfolio_snapshots(timestamp)` — prevents slow queries as data grows
- **D-05:** Foreign keys enabled (`PRAGMA foreign_keys=ON`) — SQLite disables them by default; must set on every connection

### Authentication
- **D-06:** Frontend uses `@supabase/supabase-js` PKCE flow (email/password only for v1 — no OAuth)
- **D-07:** Backend verifies JWTs using `PyJWT` + JWKS key rotation (caching Supabase's public keys, NOT using `supabase-py` client library)
- **D-08:** JWT middleware on all FastAPI routes (except `/health` and `/docs`) — WebSocket connections also validate JWT on connect
- **D-09:** Session persistence across browser refreshes handled by Supabase client SDK (`getSession()` on mount) — no custom session management needed
- **D-10:** Logout clears Supabase client session + redirects to login page — no server-side session invalidation (stateless JWT)

### Project Structure
- **D-11:** Monorepo with `/frontend` and `/backend` directories at project root — shared `docker-compose.yml` and `.env` at root level
- **D-12:** Backend structure follows FastAPI convention: `backend/app/main.py` (FastAPI app), `backend/app/routers/`, `backend/app/models/` (SQLAlchemy), `backend/app/dependencies.py` (DB session, auth)
- **D-13:** Frontend structure: `frontend/src/App.tsx`, `frontend/src/pages/`, `frontend/src/components/`, `frontend/src/hooks/`, `frontend/src/lib/` (supabase client, API client)
- **D-14:** Alembic lives in `backend/alembic/` with `alembic.ini` at `backend/alembic.ini` — standard layout, runs from backend directory
- **D-15:** Shared environment variables via root `.env` file — `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_JWT_SECRET`, `DATABASE_URL`

### Login Page UX
- **D-16:** Minimal login page — email + password fields, centered card on dark background, Supabase Auth handles all validation/errors
- **D-17:** Error messages displayed inline below the form (Supabase error messages mapped to user-friendly text)
- **D-18:** After successful login, redirect to dashboard root (`/`) — React Router handles route protection via auth guard
- **D-19:** Protected routes wrapper component checks Supabase session on mount, redirects to `/login` if no session

### Migration Strategy
- **D-20:** Alembic `autogenerate` from SQLAlchemy models — single source of truth for schema in Python code
- **D-21:** Initial migration creates all 4 tables with indexes and WAL pragma setup
- **D-22:** Database file stored at `backend/data/trading.db` — gitignored, created on first migration run
- **D-23:** `aiosqlite` for async database access in FastAPI (sync SQLAlchemy models + async engine via `create_async_engine`)

### Claude's Discretion
- Exact column names and types for each table (follow SQLAlchemy naming conventions)
- Supabase error message mapping to user-friendly text
- Login page visual styling details beyond "minimal centered card on dark background"
- Frontend package versions (use latest stable at time of implementation)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Context
- `.planning/PROJECT.md` — Project vision, tech stack decisions, constraints, key decisions table
- `.planning/REQUIREMENTS.md` — INFRA-01, INFRA-02, AUTH-01, AUTH-02, AUTH-03, AUTH-04 (Phase 1 requirements)
- `.planning/ROADMAP.md` — Phase 1 success criteria and scope boundary
- `.planning/STATE.md` — Current project position

### Research
- `.planning/research/SUMMARY.md` — Executive summary, stack validation, architecture approach, critical pitfalls
- `.planning/research/ARCHITECTURE.md` — Component boundaries, data flow, event-driven pattern
- `.planning/research/STACK.md` — Technology recommendations with versions
- `.planning/research/PITFALLS.md` — Domain pitfalls with mitigations (esp. SQLite WAL contention, JWKS cache)

### Existing Codebase
- `config.py` — Risk parameters, fee structure, timeframe configs (source of truth for bot config values)
- `testing/realtime_testing.py` — Current state persistence via JSON files (the code being replaced by SQLite)
- `testing/backtesting.py` — Trade execution logic reference (position/trade data structures)

### Supabase Auth
- `https://supabase.com/docs/guides/auth` — PKCE flow, session management, JWT structure
- `https://supabase.com/docs/guides/auth/server-side` — JWT verification on backend

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `config.py`: Risk parameters (MAKER_FEE_CEX, TAKER_FEE_CEX, RISK_PCTS, SIGNAL_THRESHOLDS) — these values inform `bot_state` default config
- `testing/realtime_testing.py`: `TradingState` class with `to_dict()`/`from_dict()` — defines the state shape that SQLite tables must represent
- `models/registry.py`: Model registry pattern — the trading engine will use `get_predictor()` instead of manual model loading

### Established Patterns
- Python package structure: each model type has its own directory with `__init__.py`, `training.py`, `evaluation.py`
- Configuration via `config.py` module-level constants + `get_timeframe_config()` function
- French/English mixed comments — follow surrounding file's convention

### Integration Points
- `realtime_testing.py` JSON file persistence → SQLite migration (replace `save_state()`/`load_state()` with DB reads/writes)
- New `backend/app/` directory — doesn't conflict with existing Python package structure (data/, models/, testing/, utils/)
- New `frontend/` directory — entirely new, no existing frontend code

</code_context>

<specifics>
## Specific Ideas

- Login page should feel like a simple admin portal — not a consumer product. Minimal, functional, dark.
- Database must be ready to receive the same data that `realtime_testing.py` currently writes to JSON — 1:1 data migration capability

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---
*Phase: 01-foundation-auth*
*Context gathered: 2026-04-25*
