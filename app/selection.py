from __future__ import annotations

import time
import uuid

from .db import get_connection


def rebuild_selection(
    symbols: list[str],
    as_of_ms: int | None = None,
    interval: str = "1m",
    top_n: int = 10,
    run_id: str | None = None,
) -> str:
    """Rebuild a point-in-time ranking using only candles ending at as_of_ms."""
    as_of_ms = as_of_ms or int(time.time() * 1000)
    run_id = run_id or uuid.uuid4().hex
    records = []
    with get_connection() as connection:
        for symbol in symbols:
            rows = connection.execute(
                """SELECT open_time, close, quote_asset_volume FROM market_klines
                   WHERE symbol=? AND interval=? AND open_time <= ?
                   AND open_time >= ? ORDER BY open_time""",
                (symbol, interval, as_of_ms, as_of_ms - 2 * 24 * 60 * 60 * 1000),
            ).fetchall()
            if len(rows) < 2:
                continue
            latest = rows[-1]
            prior = next((row for row in rows if row[0] >= as_of_ms - 24 * 60 * 60 * 1000), None)
            if prior is None or prior[1] <= 0:
                continue
            change = (latest[1] - prior[1]) / prior[1] * 100.0
            volume = sum(float(row[2]) for row in rows if row[0] >= as_of_ms - 24 * 60 * 60 * 1000)
            score = max(change, 0.0) + min(volume / 1_000_000.0, 20.0)
            records.append((symbol, change, volume, float(latest[1]), score))
        records.sort(key=lambda item: (item[4], item[1], item[2]), reverse=True)
        connection.executemany(
            """INSERT INTO historical_selection
            (run_id, as_of_ms, symbol, rank, pct_change_24h, volume_usdt,
             price, quality_score, is_eligible) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (run_id, as_of_ms, item[0], rank, item[1], item[2], item[3], item[4], int(rank <= top_n))
                for rank, item in enumerate(records, 1)
            ],
        )
    return run_id
