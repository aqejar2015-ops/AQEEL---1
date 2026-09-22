from __future__ import annotations

import sqlite3
from pathlib import Path

from .config import settings


def get_connection() -> sqlite3.Connection:
    Path(settings.db_path).parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(settings.db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def init_db() -> None:
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS market_klines (
                symbol TEXT NOT NULL,
                interval TEXT NOT NULL,
                open_time INTEGER NOT NULL,
                close_time INTEGER NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL NOT NULL,
                quote_asset_volume REAL NOT NULL,
                number_of_trades INTEGER NOT NULL,
                taker_buy_base_asset_volume REAL NOT NULL,
                taker_buy_quote_asset_volume REAL NOT NULL,
                PRIMARY KEY (symbol, interval, open_time)
            );
            CREATE INDEX IF NOT EXISTS idx_klines_symbol_time
                ON market_klines(symbol, interval, open_time);

            CREATE TABLE IF NOT EXISTS archive_runs (
                run_id TEXT PRIMARY KEY,
                interval TEXT NOT NULL,
                start_ms INTEGER NOT NULL,
                end_ms INTEGER NOT NULL,
                symbol_count INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'running',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                finished_at TEXT
            );

            CREATE TABLE IF NOT EXISTS historical_selection (
                run_id TEXT NOT NULL,
                as_of_ms INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                rank INTEGER NOT NULL,
                pct_change_24h REAL NOT NULL,
                volume_usdt REAL NOT NULL,
                price REAL NOT NULL,
                quality_score REAL NOT NULL,
                is_eligible INTEGER NOT NULL,
                PRIMARY KEY (run_id, symbol)
            );
            """
        )
