from __future__ import annotations

from typing import Any

import requests

from crypto_intelligence.config.settings import settings


class BinanceRestClient:
    """Public Binance REST client. No trading or account APIs are used."""

    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or settings.binance_base_url).rstrip("/")
        self.session = requests.Session()

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        response = self.session.get(
            f"{self.base_url}{path}",
            params=params or {},
            timeout=settings.request_timeout_seconds,
        )
        response.raise_for_status()
        return response.json()

    def get_exchange_info(self) -> dict[str, Any]:
        return self.get("/api/v3/exchangeInfo")

    def get_klines(
        self,
        symbol: str,
        interval: str,
        start_ms: int,
        end_ms: int,
        limit: int = 1000,
    ) -> list[list[Any]]:
        return self.get(
            "/api/v3/klines",
            params={
                "symbol": symbol,
                "interval": interval,
                "startTime": start_ms,
                "endTime": end_ms,
                "limit": limit,
            },
        )

    def get_usdt_symbols(self) -> list[str]:
        info = self.get_exchange_info()
        symbols = []
        for item in info.get("symbols", []):
            if item.get("status") != "TRADING":
                continue
            if item.get("quoteAsset") != "USDT":
                continue
            if not item.get("isSpotTradingAllowed", True):
                continue
            symbols.append(item["symbol"])
        return sorted(symbols)
