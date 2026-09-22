from __future__ import annotations

import threading
import webbrowser

import uvicorn

from crypto_intelligence.dashboard.stocks_server import app


def main() -> None:
    host, port = "127.0.0.1", 8001
    url = f"http://{host}:{port}"
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    print(f"CIOE US stocks dashboard: {url}")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
