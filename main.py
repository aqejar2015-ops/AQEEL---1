from __future__ import annotations

import argparse

from app.archive import build_archive
from app.binance_client import BinanceClient
from app.db import init_db
from app.selection import rebuild_selection


def main() -> None:
    parser = argparse.ArgumentParser(description="AQEEL offline Binance market archive")
    parser.add_argument("--days", type=int, default=1, help="Days to download; use 30 for the full archive")
    parser.add_argument("--limit-symbols", type=int, default=5, help="Limit symbols for a safe first test")
    parser.add_argument("--full", action="store_true", help="Download all USDT symbols")
    parser.add_argument("--skip-archive", action="store_true")
    args = parser.parse_args()

    init_db()
    client = BinanceClient()
    symbols = client.get_usdt_symbols()
    if not args.full:
        symbols = symbols[: args.limit_symbols]
    print(f"Using {len(symbols)} symbols: {', '.join(symbols)}")

    if not args.skip_archive:
        run_id = build_archive(symbols, days=args.days)
        print(f"Archive run completed: {run_id}")
    selection_id = rebuild_selection(symbols, top_n=min(10, len(symbols)))
    print(f"Historical selection completed: {selection_id}")


if __name__ == "__main__":
    main()
