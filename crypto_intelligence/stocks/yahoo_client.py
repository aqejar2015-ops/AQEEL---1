from __future__ import annotations

from typing import Any

import requests

from crypto_intelligence.config.settings import settings


class YahooStockClient:
    """Public Yahoo Finance chart reader for research/display only.

    This client does not place orders and does not require brokerage credentials.
    Yahoo Finance availability/rate limits can change; failures are reported to the UI.
    """

    base_url = "https://query1.finance.yahoo.com/v8/finance/chart"

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "CIOE-research/1.0"})

    def get_klines(self, symbol: str, interval: str = "1m", range_: str = "1d") -> list[list[Any]]:
        response = self.session.get(
            f"{self.base_url}/{symbol}",
            params={"interval": interval, "range": range_, "events": "div,splits"},
            timeout=settings.request_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json().get("chart", {})
        if payload.get("error"):
            raise RuntimeError(str(payload["error"]))
        result = (payload.get("result") or [None])[0]
        if not result:
            raise RuntimeError(f"No chart data returned for {symbol}")
        timestamps = result.get("timestamp") or []
        quote = (result.get("indicators", {}).get("quote") or [{}])[0]
        rows: list[list[Any]] = []
        for i, timestamp in enumerate(timestamps):
            values = [quote.get(key, [None] * len(timestamps))[i] for key in ("open", "high", "low", "close", "volume")]
            if any(value is None for value in values):
                continue
            # Adapt Yahoo rows to the same shape consumed by technical.analyze_candles:
            # [open_time, open, high, low, close, volume].
            rows.append([int(timestamp) * 1000, *[float(value) for value in values]])
        return rows

    def get_us_stock_symbols(self) -> list[str]:
        return [symbol.strip().upper() for symbol in settings.us_stock_symbols.split(",") if symbol.strip()]
