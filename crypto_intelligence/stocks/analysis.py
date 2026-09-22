from __future__ import annotations

from typing import Any

import requests

from crypto_intelligence.config.settings import settings


class YahooStockClient:
    """Public Yahoo Finance reader for top-gainers and OHLC data only."""

    screener_url = "https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved"
    chart_url = "https://query1.finance.yahoo.com/v8/finance/chart"

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "CIOE-research/1.0"})

    def get_top_gainers(self, limit: int = 7) -> list[str]:
        params = {
            "formatted": "true",
            "lang": "en-US",
            "region": "US",
            "scrIds": "day_gainers",
            "count": max(20, limit * 4),
        }
        response = self.session.get(self.screener_url, params=params, timeout=settings.request_timeout_seconds)
        response.raise_for_status()
        payload = response.json()
        quotes: list[dict[str, Any]] = []
        for result in payload.get("finance", {}).get("result", []):
            quotes.extend(result.get("quotes", []))
        symbols: list[str] = []
        for item in quotes:
            symbol = str(item.get("symbol", "")).strip().upper()
            if not symbol or item.get("quoteType") == "EQUITY" and not symbol.endswith(".US"):
                # Allow normal exchange-listed symbols; filter once they are known to be valid.
                pass
            if symbol:
                symbols.append(symbol)
        # Deduplicate while preserving order.
        seen: set[str] = set()
        ordered: list[str] = []
        for symbol in symbols:
            if symbol in seen:
                continue
            seen.add(symbol)
            ordered.append(symbol)
        return ordered[:limit]

    def get_klines(self, symbol: str, interval: str = "1m", range_: str = "1d") -> list[list[Any]]:
        response = self.session.get(
            f"{self.chart_url}/{symbol}",
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
            rows.append([int(timestamp) * 1000, *[float(value) for value in values]])
        return rows

    def get_us_stock_symbols(self) -> list[str]:
        return [symbol.strip().upper() for symbol in settings.us_stock_symbols.split(",") if symbol.strip()]
