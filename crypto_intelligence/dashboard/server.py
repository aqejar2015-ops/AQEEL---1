from __future__ import annotations

import asyncio
import logging
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

import requests
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from crypto_intelligence.analysis.technical import analyze_candles
from crypto_intelligence.config.settings import settings
from crypto_intelligence.stocks.analysis import fetch_stock_analysis

logger = logging.getLogger("cioe.dashboard")
_lock = threading.Lock()
_state: dict[str, Any] = {
    "status": "STARTING",
    "updated_at": None,
    "crypto": [],
    "stocks": [],
    "errors": [],
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _binance(path: str, params: dict[str, Any] | None = None) -> Any:
    response = requests.get(f"{settings.binance_base_url}{path}", params=params or {}, timeout=settings.request_timeout_seconds)
    response.raise_for_status()
    return response.json()


def _fetch_crypto() -> list[dict[str, Any]]:
    rows = _binance("/api/v3/ticker/24hr")
    excluded = {"USDCUSDT", "BUSDUSDT", "FDUSDUSDT", "TUSDUSDT", "DAIUSDT"}
    candidates = []
    for row in rows:
        symbol = str(row.get("symbol", ""))
        if not symbol.endswith("USDT") or symbol in excluded:
            continue
        try:
            price = float(row["lastPrice"]); change = float(row["priceChangePercent"]); volume = float(row["quoteVolume"])
        except (KeyError, TypeError, ValueError):
            continue
        if price > 0 and volume > 0:
            candidates.append((symbol, price, change, volume))
    candidates.sort(key=lambda x: (x[2], x[3]), reverse=True)
    result = []
    for symbol, price, change, volume in candidates[: settings.selected_coin_count]:
        try:
            one = _binance("/api/v3/klines", {"symbol": symbol, "interval": "1m", "limit": 240})
            five = _binance("/api/v3/klines", {"symbol": symbol, "interval": "5m", "limit": 200})
            fifteen = _binance("/api/v3/klines", {"symbol": symbol, "interval": "15m", "limit": 100})
            a1, a5, a15 = analyze_candles(one, five), analyze_candles(five, fifteen), analyze_candles(fifteen)
            score = round(a1.score * .2 + a5.score * .3 + a15.score * .5, 2)
            direction = "UP" if score >= 58 else "DOWN" if score <= 42 else "FLAT"
            recommendation = "BUY" if direction == "UP" and score >= 65 else "SELL" if direction == "DOWN" and score <= 35 else "HOLD"
            result.append({"symbol": symbol, "price": price, "change_24h": change, "volume_usdt": volume, "score": score, "direction": direction, "recommendation": recommendation, "rsi": a1.rsi, "atr_percent": a1.atr_percent, "reasons": (a1.reasons + a5.reasons + a15.reasons)[:4]})
        except Exception as exc:
            logger.warning("Crypto %s skipped: %s", symbol, exc)
    return result


def refresh_all() -> None:
    errors: list[str] = []
    try:
        crypto = _fetch_crypto()
    except Exception as exc:
        crypto = []
        errors.append(f"Crypto: {exc}")
    try:
        stocks = fetch_stock_analysis()
    except Exception as exc:
        stocks = []
        errors.append(f"Stocks: {exc}")
    with _lock:
        _state.update({"status": "CONNECTED" if not errors else "PARTIAL", "updated_at": _now_iso(), "crypto": crypto, "stocks": stocks, "errors": errors})


async def _refresh_loop() -> None:
    while True:
        await asyncio.to_thread(refresh_all)
        await asyncio.sleep(settings.analysis_interval_seconds)


@asynccontextmanager
async def lifespan(_: FastAPI):
    task = asyncio.create_task(_refresh_loop())
    yield
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)


app = FastAPI(title="CIOE Unified Dashboard", lifespan=lifespan)


@app.get("/api/all")
def all_data() -> dict[str, Any]:
    with _lock:
        return dict(_state)


@app.post("/api/refresh")
def manual_refresh() -> dict[str, Any]:
    refresh_all()
    return all_data()


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return """<!doctype html><html lang='ar' dir='rtl'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>CIOE Unified Dashboard</title><style>body{margin:0;background:#08131c;color:#eaf4ff;font-family:Segoe UI,Arial,sans-serif}main{max-width:1500px;margin:auto;padding:24px}h1{margin:0 0 5px}.muted{color:#9fb2c3}.bar{display:flex;gap:18px;align-items:center;flex-wrap:wrap;margin:18px 0}.badge{padding:6px 12px;border-radius:999px;background:#17633b}.partial{background:#9a681b}.error{background:#7c2929}button{background:#1683d8;border:0;color:#fff;border-radius:6px;padding:9px 15px;cursor:pointer}h2{margin-top:28px}table{width:100%;border-collapse:collapse;background:#0e202c;margin-bottom:20px}th,td{padding:10px 7px;border-bottom:1px solid #203747;text-align:center}th{color:#9fb2c3}.up,.buy{color:#45d483;font-weight:700}.down,.sell{color:#ff7272;font-weight:700}.flat,.hold{color:#ffd166;font-weight:700}.why{text-align:right;font-size:12px}a{color:#8fc6ff}.errorbox{color:#ffb86b}</style></head><body><main><h1>لوحة CIOE الموحدة</h1><div class='muted'>7 عملات رقمية + 7 أسهم أمريكية — تحليل فني وتوصيات بحثية فقط، بدون تنفيذ صفقات.</div><div class='bar'><span id='status' class='badge'>STARTING</span><span>آخر تحديث: <b id='updated'>-</b></span><button onclick='refreshNow()'>تحديث الكل الآن</button></div><div id='errors' class='errorbox'></div><h2>العملات الرقمية — أعلى 7 ارتفاعًا</h2><table><thead><tr><th>#</th><th>الرمز</th><th>السعر</th><th>24H %</th><th>الدرجة</th><th>الاتجاه</th><th>التوصية</th><th>RSI</th><th>ATR %</th></tr></thead><tbody id='crypto'><tr><td colspan='9'>جاري التحميل...</td></tr></tbody></table><h2>الأسهم الأمريكية — أعلى 7 ارتفاعًا</h2><table><thead><tr><th>#</th><th>السهم</th><th>السعر</th><th>التغير %</th><th>الدرجة</th><th>الاتجاه</th><th>التوصية</th><th>الثقة</th><th>TradingView</th></tr></thead><tbody id='stocks'><tr><td colspan='9'>جاري التحميل...</td></tr></tbody></table><div class='muted'>التحديث التلقائي كل 120 ثانية. BUY/SELL/HOLD ليست نصيحة مالية أو ضمانًا.</div></main><script>const n=x=>x==null?'-':Number(x).toLocaleString(undefined,{maximumFractionDigits:4});const cls=x=>x==='UP'||x==='BUY'?'up':x==='DOWN'||x==='SELL'?'down':'flat';function cryptoRows(a){return (a||[]).map((x,i)=>`<tr><td>${i+1}</td><td><b>${x.symbol}</b></td><td>${n(x.price)}</td><td class='${x.change_24h>=0?'up':'down'}'>${Number(x.change_24h).toFixed(2)}%</td><td>${n(x.score)}</td><td class='${cls(x.direction)}'>${x.direction}</td><td class='${cls(x.recommendation)}'>${x.recommendation}</td><td>${n(x.rsi)}</td><td>${n(x.atr_percent)}</td></tr>`).join('')||'<tr><td colspan="9">لا توجد بيانات</td></tr>'}function stockRows(a){return (a||[]).map((x,i)=>x.error?`<tr><td>${i+1}</td><td>${x.symbol}</td><td colspan='7' class='down'>${x.error}</td></tr>`:`<tr><td>${i+1}</td><td><b>${x.symbol}</b></td><td>${n(x.price)}</td><td class='${x.change_24h>=0?'up':'down'}'>${Number(x.change_24h).toFixed(2)}%</td><td>${n(x.score)}</td><td class='${cls(x.direction)}'>${x.direction}</td><td class='${cls(x.recommendation)}'>${x.recommendation} / ${x.recommendation_ar||''}</td><td>${x.confidence?Number(x.confidence*100).toFixed(1)+'%':'-'}</td><td><a target='_blank' href='${x.chart_url||'#'}'>فتح</a></td></tr>`).join('')||'<tr><td colspan="9">لا توجد بيانات</td></tr>'}async function load(){try{const d=await (await fetch('/api/all',{cache:'no-store'})).json();const s=document.getElementById('status');s.textContent=d.status;s.className='badge '+(d.status==='PARTIAL'?'partial':'');document.getElementById('updated').textContent=d.updated_at||'-';document.getElementById('errors').textContent=(d.errors||[]).join(' | ');document.getElementById('crypto').innerHTML=cryptoRows(d.crypto);document.getElementById('stocks').innerHTML=stockRows(d.stocks)}catch(e){document.getElementById('status').textContent='OFFLINE'}}async function refreshNow(){document.getElementById('status').textContent='UPDATING';await fetch('/api/refresh',{method:'POST'});await load()}load();setInterval(load,10000)</script></body></html>"""
