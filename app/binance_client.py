from __future__ import annotations

import time
from typing import Any

import requests

from .config import settings


class BinanceClient:
    """Small public Binance Spot REST client with bounded retries."""

    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or settings.binance_base_url).rstrip("/")
        self.session = requests.Session()

    def _request(self, path: str, params: dict[str, Any] | None = None) -> Any:
        last_error: Exception | None = None
        for attempt in range(settings.max_retries):
            try:
                response = self.session.get(
                    f"{self.base_url}{path}",
                    params=params,
                    timeout=settings.request_timeout,
                )
                if response.status_code == 200:
                    return response.json()
                if response.status_code not in {418, 429, 500, 502, 503, 504}:
                    response.raise_for_status()
                last_error = RuntimeError(
                    f"Binance HTTP {response.status_code}: {response.text[:300]}"
                )
            except requests.RequestException as exc:
                last_error = exc
            if attempt + 1 < settings.max_retries:
                time.sleep(settings.retry_delay_seconds * (attempt + 1))
        raise RuntimeError("Binance request failed after retries") from last_error

    def get_usdt_symbols(self) -> list[str]:
        data = self._request("/api/v3/exchangeInfo")
        return sorted(
            item["symbol"]
            for item in data.get("symbols", [])
            if item.get("status") == "TRADING"
            and item.get("quoteAsset") == "USDT"
            and item.get("isSpotTradingAllowed", True)
        )

    def get_klines(
        self,
        symbol: str,
        start_ms: int,
        end_ms: int,
        interval: str = "1m",
    ) -> list[list[Any]]:
        return self._request(
            "/api/v3/klines",
            {
                "symbol": symbol,
                "interval": interval,
                "startTime": start_ms,
                "endTime": end_ms,
                "limit": settings.request_limit,
            },
        )
