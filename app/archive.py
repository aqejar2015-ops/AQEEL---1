from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone

from .binance_client import BinanceClient
from .config import settings
from .db import get_connection


DAY_MS = 24 * 60 * 60 * 1000
MINUTE_MS = 60 * 1000


def _insert_klines(symbol: str, interval: str, rows: list[list[object]]) -> int:
    values = []
    for row in rows:
        if len(row) < 12:
            continue
        values.append(
            (
                symbol, interval, int(row[0]), int(row[6]), float(row[1]),
                float(row[2]), float(row[3]), float(row[4]), float(row[5]),
                float(row[7]), int(row[8]), float(row[9]), float(row[10]),
            )
        )
    if not values:
        return 0
    with get_connection() as connection:
        connection.executemany(
            """INSERT OR REPLACE INTO market_klines
            (symbol, interval, open_time, close_time, open, high, low, close,
             volume, quote_asset_volume, number_of_trades,
             taker_buy_base_asset_volume, taker_buy_quote_asset_volume)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            values,
        )
    return len(values)


def archive_symbol(
    client: BinanceClient,
    symbol: str,
    days: int = 30,
    interval: str = "1m",
    end_ms: int | None = None,
) -> int:
    end_ms = end_ms or int(time.time() * 1000)
    start_ms = end_ms - days * DAY_MS
    cursor = start_ms
    total = 0
    while cursor < end_ms:
        batch = client.get_klines(symbol, cursor, end_ms, interval)
        if not batch:
            break
        total += _insert_klines(symbol, interval, batch)
        next_cursor = int(batch[-1][0]) + MINUTE_MS
        if next_cursor <= cursor:
            break
        cursor = next_cursor
        if len(batch) < settings.request_limit:
            break
    return total


def build_archive(symbols: list[str], days: int = 30, interval: str = "1m") -> str:
    run_id = uuid.uuid4().hex
    end_ms = int(time.time() * 1000)
    start_ms = end_ms - days * DAY_MS
    with get_connection() as connection:
        connection.execute(
            "INSERT INTO archive_runs(run_id, interval, start_ms, end_ms, symbol_count) VALUES (?, ?, ?, ?, ?)",
            (run_id, interval, start_ms, end_ms, len(symbols)),
        )
    client = BinanceClient()
    status = "completed"
    try:
        for index, symbol in enumerate(symbols, 1):
            count = archive_symbol(client, symbol, days, interval, end_ms)
            print(f"[{index}/{len(symbols)}] {symbol}: {count} candles")
    except Exception:
        status = "failed"
        raise
    finally:
        with get_connection() as connection:
            connection.execute(
                "UPDATE archive_runs SET status=?, finished_at=? WHERE run_id=?",
                (status, datetime.now(timezone.utc).isoformat(), run_id),
            )
    return run_id
