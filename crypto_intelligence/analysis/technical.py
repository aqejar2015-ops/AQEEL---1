from __future__ import annotations

from dataclasses import asdict, dataclass
from math import sqrt
from statistics import mean
from typing import Iterable


@dataclass
class TechnicalAnalysis:
    direction: str
    signal: str
    score: float
    confidence: float
    trend: str
    reasons: list[str]
    contradictions: list[str]
    rsi: float | None
    macd_histogram: float | None
    ema_fast: float | None
    ema_slow: float | None
    bollinger_position: float | None
    atr_percent: float | None

    def to_dict(self) -> dict:
        return asdict(self)


def _ema(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    value = mean(values[:period])
    alpha = 2.0 / (period + 1.0)
    for item in values[period:]:
        value = alpha * item + (1.0 - alpha) * value
    return value


def _rsi(values: list[float], period: int = 14) -> float | None:
    if len(values) <= period:
        return None
    gains = [max(values[i] - values[i - 1], 0.0) for i in range(1, len(values))]
    losses = [max(values[i - 1] - values[i], 0.0) for i in range(1, len(values))]
    avg_gain = mean(gains[:period])
    avg_loss = mean(losses[:period])
    for gain, loss in zip(gains[period:], losses[period:]):
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
    if avg_loss == 0:
        return 100.0
    return 100.0 - (100.0 / (1.0 + avg_gain / avg_loss))


def _std(values: Iterable[float]) -> float:
    values = list(values)
    if len(values) < 2:
        return 0.0
    average = mean(values)
    return sqrt(sum((x - average) ** 2 for x in values) / len(values))


def analyze_candles(rows: list[list], higher_rows: list[list] | None = None) -> TechnicalAnalysis:
    """Explainable baseline analysis of closed Binance candles; no order execution."""
    rows = rows[:-1] if len(rows) > 1 else rows  # ignore the currently forming candle
    closes = [float(row[4]) for row in rows]
    highs = [float(row[2]) for row in rows]
    lows = [float(row[3]) for row in rows]
    volumes = [float(row[5]) for row in rows]
    if len(closes) < 30 or any(x <= 0 for x in closes):
        return TechnicalAnalysis("UNKNOWN", "DATA_INVALID", 0, 0, "UNKNOWN", [], ["Not enough valid candles"], None, None, None, None, None, None)

    price = closes[-1]
    ema9, ema20, ema50 = _ema(closes, 9), _ema(closes, 20), _ema(closes, 50)
    rsi = _rsi(closes)
    fast, slow = _ema(closes, 12), _ema(closes, 26)
    macd_hist = None
    if fast is not None and slow is not None:
        signal_line = _ema(closes[-len(closes) + 26:], 9)
        macd_hist = (fast - slow) - ((signal_line or (fast - slow)))
    window = closes[-20:]
    basis, deviation = mean(window), _std(window)
    upper, lower = basis + 2 * deviation, basis - 2 * deviation
    bb_position = (price - lower) / (upper - lower) if upper > lower else 0.5
    true_ranges = [max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1])) for i in range(1, len(closes))]
    atr = mean(true_ranges[-14:]) if len(true_ranges) >= 14 else None
    atr_percent = (atr / price * 100.0) if atr is not None else None

    score = 50.0
    reasons: list[str] = []
    contradictions: list[str] = []
    if ema9 and ema20:
        if price > ema9 > ema20:
            score += 22; reasons.append("السعر أعلى من EMA9 وEMA20")
        elif price < ema9 < ema20:
            score -= 22; reasons.append("السعر أسفل EMA9 وEMA20")
        else:
            contradictions.append("تقاطع متوسطات غير حاسم")
    if rsi is not None:
        if 52 <= rsi <= 68:
            score += 12; reasons.append(f"RSI داعم ({rsi:.1f})")
        elif 32 <= rsi < 48:
            score -= 12; reasons.append(f"RSI ضعيف ({rsi:.1f})")
        elif rsi > 75:
            contradictions.append(f"RSI مرتفع جدًا ({rsi:.1f})")
        elif rsi < 25:
            contradictions.append(f"RSI منخفض جدًا ({rsi:.1f})")
    if macd_hist is not None:
        if macd_hist > 0:
            score += 10; reasons.append("MACD histogram موجب")
        else:
            score -= 10; reasons.append("MACD histogram سالب")
    if len(volumes) >= 30 and mean(volumes[-5:]) > mean(volumes[-25:-5]) * 1.2:
        if closes[-1] > closes[-2]:
            score += 6; reasons.append("ارتفاع حجم مع شمعة صاعدة")
        else:
            score -= 6; reasons.append("ارتفاع حجم مع شمعة هابطة")
    if bb_position > 0.8:
        contradictions.append("السعر قريب من الحد العلوي للتذبذب")
    elif bb_position < 0.2:
        contradictions.append("السعر قريب من الحد السفلي للتذبذب")

    if higher_rows:
        higher = analyze_candles(higher_rows)
        if higher.direction == "DOWN" and score > 50:
            score -= 8; contradictions.append("الإطار الأعلى هابط")
        elif higher.direction == "UP" and score < 50:
            score += 8; contradictions.append("الإطار الأعلى صاعد")

    score = max(0.0, min(100.0, score))
    direction = "UP" if score >= 58 else "DOWN" if score <= 42 else "FLAT"
    signal = "BULLISH" if direction == "UP" else "BEARISH" if direction == "DOWN" else "NEUTRAL"
    confidence = round(min(0.95, 0.50 + abs(score - 50) / 100.0), 3)
    trend = "UPTREND" if ema20 and price > ema20 else "DOWNTREND" if ema20 else "UNKNOWN"
    return TechnicalAnalysis(direction, signal, round(score, 2), confidence, trend, reasons, contradictions, round(rsi, 2) if rsi is not None else None, macd_hist, ema9, ema20, round(bb_position, 3), round(atr_percent, 4) if atr_percent is not None else None)
