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

from crypto_intelligence.config.settings import settings
from crypto_intelligence.database.repository import DatabaseRepository

logger = logging.getLogger("cioe.dashboard")

_state: dict[str, Any] = {
    "status": "STARTING",
    "updated_at": None,
    "next_analysis_at": None,
    "symbols": [],
    "error": None,
}
_lock = threading.Lock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fetch_market() -> list[dict[str, Any]]:
    """Fetch public 24h Spot ticker data; never uses trading/account APIs."""
    response = requests.get(
        f"{settings.binance_base_url}/api/v3/ticker/24hr",
        timeout=settings.request_timeout_seconds,
    )
    response.raise_for_status()
    rows = response.json()
    candidates = []
    excluded = ("USDCUSDT", "BUSDUSDT", "FDUSDUSDT", "TUSDUSDT", "DAIUSDT")
    for row in rows:
        symbol = str(row.get("symbol", ""))
        if not symbol.endswith("USDT") or symbol in excluded:
            continue
        try:
            price = float(row["lastPrice"])
            change = float(row["priceChangePercent"])
            volume = float(row["quoteVolume"])
            trades = int(row.get("count", 0))
        except (KeyError, TypeError, ValueError):
            continue
        if price <= 0 or volume <= 0:
            continue
        candidates.append(
            {
                "symbol": symbol,
                "price": price,
                "change_24h": change,
                "volume_usdt": volume,
                "trades": trades,
                "score": round(max(0.0, min(100.0, 50.0 + change * 2.0)), 2),
                "trend": "BULLISH" if change > 1 else "BEARISH" if change < -1 else "NEUTRAL",
                "opportunity": "WATCH",
            }
        )
    candidates.sort(key=lambda item: (item["change_24h"], item["volume_usdt"]), reverse=True)
    return candidates[: settings.selected_coin_count]


def refresh_market() -> None:
    try:
        symbols = _fetch_market()
        now = time.time()
        with _lock:
            _state.update(
                {
                    "status": "CONNECTED",
                    "updated_at": _now_iso(),
                    "next_analysis_at": datetime.fromtimestamp(
                        now + settings.analysis_interval_seconds, timezone.utc
                    ).isoformat(),
                    "symbols": symbols,
                    "error": None,
                }
            )
        logger.info("Market refresh completed: %s symbols", len(symbols))
    except Exception as exc:  # one failed refresh must not stop the dashboard
        logger.exception("Market refresh failed")
        with _lock:
            _state.update({"status": "ERROR", "error": str(exc), "updated_at": _now_iso()})


async def _market_loop() -> None:
    while True:
        await asyncio.to_thread(refresh_market)
        await asyncio.sleep(settings.analysis_interval_seconds)


@asynccontextmanager
async def lifespan(_: FastAPI):
    repository = DatabaseRepository()
    repository.init_schema()
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
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>CIOE Dashboard</title>
<style>
body{margin:0;background:#08131c;color:#eaf4ff;font-family:Segoe UI,Arial,sans-serif}main{max-width:1250px;margin:auto;padding:28px}h1{margin:0 0 8px}.muted{color:#9fb2c3}.bar{display:flex;gap:18px;align-items:center;flex-wrap:wrap;margin:22px 0}.badge{padding:6px 12px;border-radius:999px;background:#214d35}.error{background:#642b2b}button{background:#1683d8;border:0;color:white;border-radius:6px;padding:9px 15px;cursor:pointer}table{width:100%;border-collapse:collapse;background:#0e202c;border-radius:8px;overflow:hidden}th,td{padding:13px 10px;border-bottom:1px solid #203747;text-align:right}th{color:#9fb2c3;text-align:right}.up{color:#45d483}.down{color:#ff7272}.neutral{color:#ffd166}.note{margin-top:18px;padding:12px;background:#132633;color:#b9cbd7}
</style></head><body><main><h1>Crypto Intelligence &amp; Opportunity Engine</h1><div class="muted">Public Binance Spot data only — Version 1 does not execute trades.</div>
<div class="bar"><span id="status" class="badge">STARTING</span><span>Last update: <b id="updated">-</b></span><button onclick="refreshNow()">REFRESH TOP 7</button></div>
<table><thead><tr><th>#</th><th>Coin</th><th>Price</th><th>24H %</th><th>Score</th><th>Trend</th><th>Opportunity</th><th>Volume USDT</th></tr></thead><tbody id="rows"><tr><td colspan="8">Loading public market data...</td></tr></tbody></table>
<div class="note">Formal refresh interval: <b id="interval"></b> seconds. The displayed ranking is informational and not financial advice.</div>
</main><script>
const money=n=>Number(n).toLocaleString(undefined,{maximumFractionDigits:8});
async function load(){try{const r=await fetch('/api/market',{cache:'no-store'}),d=await r.json();const s=document.getElementById('status');s.textContent=d.status;s.className='badge '+(d.status==='ERROR'?'error':'');document.getElementById('updated').textContent=d.updated_at||'-';document.getElementById('interval').textContent=Math.round((d.next_analysis_at?1:1)*120);if(d.error){document.getElementById('rows').innerHTML='<tr><td colspan="8">'+d.error+'</td></tr>';return}document.getElementById('rows').innerHTML=(d.symbols||[]).map((x,i)=>`<tr><td>${i+1}</td><td><b>${x.symbol}</b></td><td>${money(x.price)}</td><td class="${x.change_24h>=0?'up':'down'}">${x.change_24h.toFixed(2)}%</td><td>${x.score.toFixed(1)}</td><td class="${x.trend==='BULLISH'?'up':x.trend==='BEARISH'?'down':'neutral'}">${x.trend}</td><td>${x.opportunity}</td><td>${money(x.volume_usdt)}</td></tr>`).join('')||'<tr><td colspan="8">No usable symbols returned.</td></tr>'}catch(e){document.getElementById('status').textContent='OFFLINE';}}
async function refreshNow(){await fetch('/api/refresh',{method:'POST'});await load()}load();setInterval(load,10000);
</script></body></html>"""
