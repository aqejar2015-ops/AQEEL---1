from __future__ import annotations

import asyncio
import threading
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from crypto_intelligence.dashboard.server import _state, _lock, _now_iso, refresh_market
from crypto_intelligence.stocks.analysis import fetch_stock_analysis


_stock_state: dict[str, Any] = {"status": "STARTING", "updated_at": None, "symbols": [], "error": None}
_stock_lock = threading.Lock()


def refresh_stocks() -> None:
    try:
        rows = fetch_stock_analysis()
        with _stock_lock:
            _stock_state.update({"status": "CONNECTED", "updated_at": _now_iso(), "symbols": rows, "error": None})
    except Exception as exc:
        with _stock_lock:
            _stock_state.update({"status": "ERROR", "updated_at": _now_iso(), "error": str(exc)})


async def _stock_loop() -> None:
    while True:
        await asyncio.to_thread(refresh_stocks)
        await asyncio.sleep(120)


@asynccontextmanager
async def lifespan(app: FastAPI):
    tasks = [asyncio.create_task(_stock_loop())]
    yield
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)


app = FastAPI(title="CIOE US Stocks", lifespan=lifespan)


@app.get("/api/stocks")
def stocks_api() -> dict[str, Any]:
    with _stock_lock:
        return dict(_stock_state)


@app.post("/api/stocks/refresh")
def stocks_refresh() -> dict[str, Any]:
    refresh_stocks()
    return stocks_api()


@app.get("/", response_class=HTMLResponse)
def stocks_home() -> str:
    return """<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>CIOE US Stocks</title><style>body{margin:0;background:#08131c;color:#eaf4ff;font-family:Segoe UI,Arial,sans-serif}main{max-width:1450px;margin:auto;padding:24px}h1{margin:0 0 5px}.muted{color:#9fb2c3}.bar{display:flex;gap:18px;align-items:center;margin:18px 0;flex-wrap:wrap}.badge{padding:6px 12px;border-radius:999px;background:#17633b}.error{background:#7c2929}button{background:#1683d8;border:0;color:#fff;border-radius:6px;padding:9px 15px;cursor:pointer}table{width:100%;border-collapse:collapse;background:#0e202c}th,td{padding:11px 8px;border-bottom:1px solid #203747;text-align:center}th{color:#9fb2c3}.up{color:#45d483;font-weight:700}.down{color:#ff7272;font-weight:700}.flat{color:#ffd166;font-weight:700}.why{text-align:right;font-size:12px;max-width:360px}</style></head><body><main><h1>تحليل الأسهم الأمريكية</h1><div class="muted">تحليل فني متعدد الأطر — بيانات عامة للبحث فقط، دون تنفيذ صفقات.</div><div class="bar"><span id="status" class="badge">STARTING</span><span>آخر تحليل: <b id="updated">-</b></span><button onclick="refreshNow()">تحديث الأسهم السبع</button></div><table><thead><tr><th>#</th><th>السهم</th><th>السعر</th><th>تغير الجلسة %</th><th>الدرجة</th><th>الاتجاه</th><th>الإشارة</th><th>الثقة النموذجية</th><th>RSI</th><th>ATR %</th><th>الأسباب والتحذيرات</th></tr></thead><tbody id="rows"><tr><td colspan="11">جاري تحميل البيانات...</td></tr></tbody></table><p class="muted">التحديث الرسمي كل 120 ثانية. الأسهم خارج ساعات السوق قد تعرض آخر بيانات متاحة.</p></main><script>const n=x=>x==null?'-':Number(x).toLocaleString(undefined,{maximumFractionDigits:4});async function load(){const d=await (await fetch('/api/stocks',{cache:'no-store'})).json();const s=document.getElementById('status');s.textContent=d.status;s.className='badge '+(d.status==='ERROR'?'error':'');document.getElementById('updated').textContent=d.updated_at||'-';document.getElementById('rows').innerHTML=(d.symbols||[]).map((x,i)=>{if(x.error)return `<tr><td>${i+1}</td><td>${x.symbol}</td><td colspan="9" class="down">${x.error}</td></tr>`;const c=x.direction==='UP'?'up':x.direction==='DOWN'?'down':'flat';return `<tr><td>${i+1}</td><td><b>${x.symbol}</b></td><td>${n(x.price)}</td><td class="${x.change_24h>=0?'up':'down'}">${x.change_24h.toFixed(2)}%</td><td>${x.score.toFixed(1)}</td><td class="${c}">${x.direction}</td><td class="${c}">${x.signal}</td><td>${(x.confidence*100).toFixed(1)}%</td><td>${n(x.rsi)}</td><td>${n(x.atr_percent)}</td><td class="why">${(x.reasons||[]).slice(0,3).join(' | ')}${(x.contradictions||[]).length?' | ⚠ '+x.contradictions.slice(0,2).join(' | '):''}</td></tr>`}).join('')||'<tr><td colspan="11">لا توجد بيانات.</td></tr>'}async function refreshNow(){document.getElementById('status').textContent='UPDATING';await fetch('/api/stocks/refresh',{method:'POST'});await load()}load();setInterval(load,10000);</script></body></html>"""
