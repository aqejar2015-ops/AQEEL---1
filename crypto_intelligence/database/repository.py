"""Storage and database access layer."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from crypto_intelligence.config.settings import settings


class DatabaseRepository:
    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or settings.db_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def init_schema(self) -> None:
        with self.get_connection() as conn:
            conn.execute(
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
                    PRIMARY KEY (symbol, interval, open_time)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS analysis_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    selected_symbols TEXT NOT NULL,
                    notes TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS rejected_candidates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    rejected_at TEXT NOT NULL,
                    reason TEXT NOT NULL
                )
                """
            )
