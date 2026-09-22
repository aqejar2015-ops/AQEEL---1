"""Minimal dashboard server with a placeholder landing page."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(title="CIOE Dashboard")


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return """
    <html>
      <head><title>CIOE</title></head>
      <body style="font-family:Segoe UI, sans-serif; background:#06131b; color:#e5f2ff; padding:24px;">
        <h1>Crypto Intelligence & Opportunity Engine</h1>
        <p>Phase 1/2 foundation is online.</p>
        <p>Dashboard work will begin after the data layer and Top-7 engine are in place.</p>
      </body>
    </html>
    """
