from __future__ import annotations

import argparse
import threading
import webbrowser

import uvicorn

from crypto_intelligence.config.settings import settings
from crypto_intelligence.dashboard.server import app


def main() -> None:
    parser = argparse.ArgumentParser(description="Unified CIOE crypto and US stocks dashboard")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    url = f"http://{args.host}:{args.port}"
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    print(f"CIOE unified dashboard: {url}")
    print("Includes seven crypto assets and seven US stocks. No trades are executed.")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
