"""Public US-equity market analysis using the same explainable baseline engine."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from crypto_intelligence.analysis.technical import analyze_candles
from crypto_intelligence.config.settings import settings
from crypto_intelligence.stocks.yahoo_client import YahooStockClient


def _price_change(rows: list[list[Any]]) -> float:
    if len(rows) < 2 or rows[-2][4] == 0:
        return 0.0
    return (float(rows[-1][4]) - float(rows[-2][4])) / float(rows[-2][4]) * 100.0


def fetch_stock_analysis() -> list[dict[str, Any]]:
    client = YahooStockClient()
    results = []
    for symbol in client.get_us_stock_symbols():
        try:
            one_min = client.get_klines(symbol, "1m", "1d")
            five_min = client.get_klines(symbol, "5m", "5d")
            fifteen_min = client.get_klines(symbol, "15m", "1mo")
            a1 = analyze_candles(one_min, five_min)
            a5 = analyze_candles(five_min, fifteen_min)
            a15 = analyze_candles(fifteen_min)
            score = round(a1.score * 0.20 + a5.score * 0.30 + a15.score * 0.50, 2)
            direction = "UP" if score >= 58 else "DOWN" if score <= 42 else "FLAT"
            results.append(
                {
                    "symbol": symbol,
                    "price": float(one_min[-1][4]) if one_min else None,
                    "change_24h": round(_price_change(one_min), 3),
                    "score": score,
                    "direction": direction,
                    "signal": "صعود" if direction == "UP" else "هبوط" if direction == "DOWN" else "محايد",
                    "confidence": round(min(0.95, 0.50 + abs(score - 50.0) / 100.0), 3),
                    "trend": a15.trend,
                    "rsi": a1.rsi,
                    "macd_histogram": a1.macd_histogram,
                    "atr_percent": a1.atr_percent,
                    "reasons": (a1.reasons + a5.reasons + a15.reasons)[:6],
                    "contradictions": (a1.contradictions + a5.contradictions + a15.contradictions)[:4],
                    "analyzed_at": datetime.now(timezone.utc).isoformat(),
                }
            )
        except Exception as exc:
            results.append({"symbol": symbol, "error": str(exc)})
    return results
