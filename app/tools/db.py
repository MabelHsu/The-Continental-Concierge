"""
Database Connection Pool — AlloyDB via asyncpg.

Single access pattern: **the async pool.** Every caller — tool functions,
FastAPI handlers, evals, CLI scripts — goes through `get_pool()` and the
`fetch_all` / `fetch_one` / `fetch_val` / `execute` / `execute_many`
helpers below. There is no synchronous wrapper and there should not be
one: calling `asyncio.run_until_complete` from inside a running loop
(which is what FastAPI gives you) raises `RuntimeError`.

The MCP Toolbox for Databases handles read-only queries in production.
This module handles all write operations and the player state layer
that the MCP Toolbox doesn't cover.

Connection string comes from environment variables set by Terraform /
Secret Manager. In local dev, use .env.template as a guide.
"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Optional

import asyncpg

logger = logging.getLogger(__name__)

# ── Pool singleton ─────────────────────────────────────────────────────────────

_pool: Optional[asyncpg.Pool] = None
_pool_lock = asyncio.Lock()


def _dsn() -> str:
    """Build postgres DSN from environment variables."""
    host = os.environ.get("ALLOYDB_HOST", "127.0.0.1")
    port = os.environ.get("ALLOYDB_PORT", "5432")
    db   = os.environ.get("ALLOYDB_DATABASE", "continental")
    user = os.environ.get("ALLOYDB_USER", "continental_app")
    pw   = os.environ.get("ALLOYDB_PASSWORD", "")
    return f"postgresql://{user}:{pw}@{host}:{port}/{db}"


async def get_pool() -> asyncpg.Pool:
    """Return (and lazily create) the shared connection pool."""
    global _pool
    if _pool is not None:
        return _pool
    async with _pool_lock:
        if _pool is None:
            _pool = await asyncpg.create_pool(
                dsn=_dsn(),
                min_size=2,
                max_size=10,
                command_timeout=30,
                server_settings={"application_name": "continental_concierge"},
            )
            logger.info("AlloyDB connection pool created.")
    return _pool


async def close_pool() -> None:
    """Gracefully close the pool on shutdown."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("AlloyDB connection pool closed.")


# ── Async query helpers ────────────────────────────────────────────────────────

@asynccontextmanager
async def transaction():
    """Context manager that yields a connection inside an explicit transaction."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            yield conn


async def fetch_all(query: str, *args: Any) -> list[dict]:
    """Execute a SELECT and return all rows as dicts."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *args)
        return [dict(r) for r in rows]


async def fetch_one(query: str, *args: Any) -> Optional[dict]:
    """Execute a SELECT and return a single row or None."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(query, *args)
        return dict(row) if row else None


async def fetch_val(query: str, *args: Any) -> Any:
    """Execute a query and return a single scalar value."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval(query, *args)


async def execute(query: str, *args: Any) -> str:
    """Execute a DML statement (INSERT/UPDATE/DELETE). Returns status string."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.execute(query, *args)


async def execute_many(query: str, args_list: list[tuple]) -> None:
    """Execute a DML statement for each tuple in args_list (bulk insert)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.executemany(query, args_list)


# NOTE: `sync_fetch_all` / `sync_fetch_one` were removed in the Phase 2
# blocker pass. They called `asyncio.get_event_loop().run_until_complete(...)`
# which raises `RuntimeError` when called from inside a running event loop —
# exactly what FastAPI's async handlers are. Callers should `await fetch_all`
# / `await fetch_one` directly. If you need DB access from true sync code
# (a CLI script, a script run under `python -m`), use `asyncio.run(...)`
# at the script entry point, not a wrapper here.
