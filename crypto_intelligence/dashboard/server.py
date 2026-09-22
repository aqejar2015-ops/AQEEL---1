"""Live dashboard and periodic public-market analysis."""

from __future__ import annotations

import asyncio
import logging
import threading
import time
import webbrowser
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

import requests
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from crypto_intelligence.analysis.technical import analyze_candles
from crypto_intelligence.config.settings import settings
from crypto_intelligence.database.repository import DatabaseRepository

logger = logging.getLogger("cioe.dashboard")
_state: dict[str, Any] = {"status": "STARTING", "updated_at": None, "next_analysis_at": None, "symbols": [], "error": None}
_lock = threading.Lock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get(path: str, params: dict[str, Any] | None = None) -> Any:
    response = requests.get(f"{settings.binance_base_url}{path}", params=params or {}, timeout=settings.request_timeout_seconds)
    response.raise_for_status()
    return response.json()


def _fetch_market() -> list[dict[str, Any]]:
    rows = _get("/api/v3/ticker/24hr")
    excluded = {"USDCUSDT", "BUSDUSDT", "FDUSDUSDT", "TUSDUSDT", "DAIUSDT"}
    candidates = []
    for row in rows:
        symbol = str(row.get("symbol", ""))
        if not symbol.endswith("USDT") or symbol in excluded:
            continue
        try:
            change, price, volume = float(row["priceChangePercent"]), float(row["lastPrice"]), float(row["quoteVolume"])
        except (KeyError, TypeError, ValueError):
            continue
        if price <= 0 or volume <= 0:
            continue
        candidates.append((symbol, price, change, volume))
    candidates.sort(key=lambda x: (x[2], x[3]), reverse=True)
    result = []
    for symbol, price, change, volume in candidates[: max(settings.selected_coin_count, 7)]:
        try:
            one_min = _get("/api/v3/klines", {"symbol": symbol, "interval": "1m", "limit": 240})
            five_min = _get("/api/v3/klines", {"symbol": symbol, "interval": "5m", "limit": 200})
            fifteen_min = _get("/api/v3/klines", {"symbol": symbol, "interval": "15m", "limit": 100})
            analysis_1m = analyze_candles(one_min, five_min)
            analysis_5m = analyze_candles(five_min, fifteen_min)
            analysis_15m = analyze_candles(fifteen_min)
            score = round(analysis_1m.score * 0.20 + analysis_5m.score * 0.30 + analysis_15m.score * 0.50, 2)
            direction = "UP" if score >= 58 else "DOWN" if score <= 42 else "FLAT"
            result.append({"symbol": symbol, "price": price, "change_24h": change, "volume_usdt": volume, "score": score, "direction": direction, "signal": "صعود" if direction == "UP" else "هبوط" if direction == "DOWN" else "محايد", "confidence": round(min(0.95, 0.5 + abs(score - 50) / 100), 3), "trend": analysis_15m.trend, "rsi": analysis_1m.rsi, "macd_histogram": analysis_1m.macd_histogram, "atr_percent": analysis_1m.atr_percent, "reasons": analysis_1m.reasons + analysis_5m.reasons + analysis_15m.reasons, "contradictions": analysis_1m.contradictions + analysis_5m.contradictions + analysis_15m.contradictions, "analyzed_at": _now_iso()})
        except Exception as exc:
            logger.warning("Skipping %s analysis: %s", symbol, exc)
    return result[: settings.selected_coin_count]


def refresh_market() -> None:
    try:
        symbols = _fetch_market()
        with _lock:
            _state.update({"status": "CONNECTED", "updated_at": _now_iso(), "next_analysis_at": datetime.fromtimestamp(time.time() + settings.analysis_interval_seconds, timezone.utc).isoformat(), "symbols": symbols, "error": None})
    except Exception as exc:
        logger.exception("Market refresh failed")
        with _lock:
            _state.update({"status": "ERROR", "error": str(exc), "updated_at": _now_iso()})


async def _market_loop() -> None:
    while True:
        await asyncio.to_thread(refresh_market)
        await asyncio.sleep(settings.analysis_interval_seconds)


@asynccontextmanager
async def lifespan(_: FastAPI):
    DatabaseRepository().init_schema()
    task = asyncio.create_task(_market_loop())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="CIOE Dashboard", lifespan=lifespan)


@app.get("/api/market")
def market() -> dict[str, Any]:
    with _lock:
        return dict(_state)


@app.post("/api/refresh")
def manual_refresh() -> dict[str, Any]:
    refresh_market()
    return market()


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return """<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>CIOE Dashboard</title><style>body{margin:0;background:#08131c;color:#eaf4ff;font-family:Segoe UI,Arial,sans-serif}main{max-width:1400px;margin:auto;padding:24px}h1{margin:0 0 6px}.muted{color:#9fb2c3}.bar{display:flex;gap:18px;align-items:center;flex-wrap:wrap;margin:18px 0}.badge{padding:6px 12px;border-radius:999px;background:#17633b}.error{background:#7c2929}button{background:#1683d8;border:0;color:white;border-radius:6px;padding:9px 15px;cursor:pointer}table{width:100%;border-collapse:collapse;background:#0e202c}th,td{padding:11px 8px;border-bottom:1px solid #203747;text-align:center}th{color:#9fb2c3}.up{color:#45d483;font-weight:700}.down{color:#ff7272;font-weight:700}.flat{color:#ffd166;font-weight:700}.why{text-align:right;font-size:12px;max-width:300px}.note{margin-top:16px;padding:12px;background:#132633;color:#b9cbd7}</style></head><body><main><h1>Crypto Intelligence &amp; Opportunity Engine</h1><div class="muted">تحليل فني متعدد الأطر لبيانات Binance العامة — لا يوجد تنفيذ صفقات حقيقية.</div><div class="bar"><span id="status" class="badge">STARTING</span><span>آخر تحليل: <b id="updated">-</b></span><button onclick="refreshNow()">تحديث العملات السبع</button></div><table><thead><tr><th>#</th><th>العملة</th><th>السعر</th><th>24H %</th><th>الدرجة</th><th>الاتجاه</th><th>الإشارة</th><th>الثقة النموذجية</th><th>RSI</th><th>ATR %</th><th>أسباب التحليل</th></tr></thead><tbody id="rows"><tr><td colspan="11">جاري تحميل البيانات...</td></tr></tbody></table><div class="note">التحديث الرسمي كل <b>120</b> ثانية. الإشارة تحليلية وليست ضمانًا أو نصيحة مالية.</div></main><script>const n=x=>x==null?'-':Number(x).toLocaleString(undefined,{maximumFractionDigits:8});async function load(){try{const d=await (await fetch('/api/market',{cache:'no-store'})).json();const s=document.getElementById('status');s.textContent=d.status;s.className='badge '+(d.status==='ERROR'?'error':'');document.getElementById('updated').textContent=d.updated_at||'-';if(d.error){document.getElementById('rows').innerHTML='<tr><td colspan="11">'+d.error+'</td></tr>';return}document.getElementById('rows').innerHTML=(d.symbols||[]).map((x,i)=>{let c=x.direction==='UP'?'up':x.direction==='DOWN'?'down':'flat';return `<tr><td>${i+1}</td><td><b>${x.symbol}</b></td><td>${n(x.price)}</td><td class="${x.change_24h>=0?'up':'down'}">${x.change_24h.toFixed(2)}%</td><td>${x.score.toFixed(1)}</td><td class="${c}">${x.direction}</td><td class="${c}">${x.signal}</td><td>${(x.confidence*100).toFixed(1)}%</td><td>${n(x.rsi)}</td><td>${n(x.atr_percent)}</td><td class="why">${(x.reasons||[]).slice(0,3).join(' | ')}${(x.contradictions||[]).length?' | ⚠ '+x.contradictions.slice(0,2).join(' | '):''}</td></tr>`}).join('')||'<tr><td colspan="11">لا توجد بيانات صالحة.</td></tr>'}catch(e){document.getElementById('status').textContent='OFFLINE'}}async function refreshNow(){document.getElementById('status').textContent='UPDATING';await fetch('/api/refresh',{method:'POST'});await load()}load();setInterval(load,10000);</script></body></html>"""
