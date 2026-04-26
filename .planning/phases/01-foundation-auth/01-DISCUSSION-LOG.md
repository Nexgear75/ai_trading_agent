# Phase 1: Foundation & Auth - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-25
**Phase:** 1-Foundation & Auth
**Areas discussed:** Database Schema, Auth Flow UX, Project Structure, Migration Strategy

---

## Database Schema

| Option | Description | Selected |
|--------|-------------|----------|
| Normalized 4-table schema with indexes | bot_state, positions, trades, portfolio_snapshots with WAL mode and strategic indexes | ✓ |
| Single wide table | One table with JSON columns for flexibility | |
| Document-style JSON columns | SQLite with JSON1 extension for semi-structured data | |

**User's choice:** Normalized 4-table schema with indexes (auto-selected — recommended)
**Notes:** WAL mode + indexes from day one prevents write contention pitfall identified in research. Schema mirrors the data structures already in `realtime_testing.py`'s `TradingState` class.

---

## Auth Flow UX

| Option | Description | Selected |
|--------|-------------|----------|
| Dedicated login page with email/password | Minimal centered card, Supabase PKCE flow, redirect to dashboard | ✓ |
| Modal overlay on dashboard | Login modal pops up over the dashboard | |
| Split: login page + persistent session | Login page on first visit, then session persists | |

**User's choice:** Dedicated login page with email/password (auto-selected — recommended)
**Notes:** Supabase client SDK handles session persistence automatically. No custom session management needed. Logout clears session + redirects.

---

## Project Structure

| Option | Description | Selected |
|--------|-------------|----------|
| Monorepo with /frontend + /backend | Two directories at project root, shared docker-compose and .env | ✓ |
| Separate repositories | Frontend and backend in different repos | |
| Monorepo with /src containing both | Both in /src with /src/frontend and /src/backend | |

**User's choice:** Monorepo with /frontend + /backend (auto-selected — recommended)
**Notes:** Standard monorepo layout. Backend follows FastAPI convention (app/ directory). Frontend follows Vite+React convention (src/ directory). Alembic in backend/alembic/.

---

## Migration Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Alembic with autogenerate from SQLAlchemy models | Single source of truth in Python code, auto-generates migration scripts | ✓ |
| Manual SQL migration files | Hand-written SQL for each migration | |
| SQLAlchemy create_all() without Alembic | Simple but no migration history or rollback | |

**User's choice:** Alembic with autogenerate from SQLAlchemy models (auto-selected — recommended)
**Notes:** Autogenerate keeps schema in sync with models. Initial migration creates all tables. aiosqlite for async access in FastAPI.

---

## Claude's Discretion

- Exact column names and types for each table
- Supabase error message mapping to user-friendly text
- Login page visual styling details beyond "minimal centered card on dark background"
- Frontend package versions

## Deferred Ideas

None — discussion stayed within phase scope.
