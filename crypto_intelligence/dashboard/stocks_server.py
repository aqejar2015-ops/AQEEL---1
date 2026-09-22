"""Top-gainer selection and explainable US-stock recommendations."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from crypto_intelligence.analysis.technical import analyze_candles
from crypto_intelligence.config.settings import settings
from crypto_intelligence.stocks.yahoo_client import YahooStockClient


def _session_change(rows: list[list[Any]]) -> float:
    if len(rows) < 2 or float(rows[-2][4]) == 0:
        return 0.0
    return (float(rows[-1][4]) - float(rows[-2][4])) / float(rows[-2][4]) * 100.0


def _recommendation(score: float, direction: str, confidence: float) -> tuple[str, str]:
    if direction == "UP" and score >= 65 and confidence >= 0.65:
        return "BUY", "Strong upward trend and higher technical score"
    if direction == "DOWN" and score <= 35 and confidence >= 0.65:
        return "SELL", "Strong downside trend and weaker technical score"
    return "HOLD", "Signal is not decisive; wait for confirmation"


def fetch_stock_analysis() -> list[dict[str, Any]]:
    client = YahooStockClient()
    top_symbols = client.get_top_gainers(limit=settings.selected_coin_count)
    if not top_symbols:
        top_symbols = client.get_us_stock_symbols()[: settings.selected_coin_count]

    selected: list[dict[str, Any]] = []
    for symbol in top_symbols:
        try:
            daily = client.get_klines(symbol, "1d", "5d")
            if len(daily) < 2:
                continue
            selected.append({
                "symbol": symbol,
                "daily_rows": daily,
                "change_24h": round(_session_change(daily), 3),
                "price": float(daily[-1][4]),
            })
        except Exception:
            continue

    if not selected:
        return [{"symbol": "N/A", "error": "No usable public stock data returned."}]

    selected.sort(key=lambda item: item["change_24h"], reverse=True)
    selected = selected[: settings.selected_coin_count]

    results: list[dict[str, Any]] = []
    for candidate in selected:
        symbol = candidate["symbol"]
        try:
            one_min = client.get_klines(symbol, "1m", "1d")
            five_min = client.get_klines(symbol, "5m", "5d")
            fifteen_min = client.get_klines(symbol, "15m", "1mo")
            a1 = analyze_candles(one_min, five_min)
            a5 = analyze_candles(five_min, fifteen_min)
            a15 = analyze_candles(fifteen_min)
            score = round(a1.score * 0.20 + a5.score * 0.30 + a15.score * 0.50, 2)
            direction = "UP" if score >= 58 else "DOWN" if score <= 42 else "FLAT"
            confidence = round(min(0.95, 0.50 + abs(score - 50.0) / 100.0), 3)
            recommendation, recommendation_reason = _recommendation(score, direction, confidence)
            results.append(
                {
                    "symbol": symbol,
                    "price": float(one_min[-1][4]) if one_min else candidate["price"],
                    "change_24h": candidate["change_24h"],
                    "score": score,
                    "direction": direction,
                    "signal": "UP" if direction == "UP" else "DOWN" if direction == "DOWN" else "FLAT",
                    "recommendation": recommendation,
                    "recommendation_ar": {"BUY": "شراء", "SELL": "بيع", "HOLD": "انتظار"}[recommendation],
                    "recommendation_reason": recommendation_reason,
                    "confidence": confidence,
                    "trend": a15.trend,
                    "rsi": a1.rsi,
                    "macd_histogram": a1.macd_histogram,
                    "atr_percent": a1.atr_percent,
                    "reasons": (a1.reasons + a5.reasons + a15.reasons)[:6],
                    "contradictions": (a1.contradictions + a5.contradictions + a15.contradictions)[:4],
                    "chart_url": f"https://www.tradingview.com/symbols/NASDAQ-{symbol}/",
                    "analyzed_at": datetime.now(timezone.utc).isoformat(),
                }
            )
        except Exception as exc:
            results.append({"symbol": symbol, "change_24h": candidate["change_24h"], "error": str(exc)})

    return sorted(results, key=lambda item: item.get("change_24h", -999), reverse=True)[: settings.selected_coin_count]
