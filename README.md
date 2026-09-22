# AQEEL - initial Python implementation

Initial safe MVP for testing the Binance public market archive and point-in-time selection.

## Windows

1. Copy `.env.example` to `.env` if you need custom settings.
2. Run:

```powershell
.\run_windows.bat
```

The default test downloads one day for five symbols. For the full 30-day archive:

```powershell
.\run_windows.bat --days 30 --full
```

## Linux/macOS

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py --days 1 --limit-symbols 5
```

Data is stored locally in `data/market_data.db`. This version uses public Binance REST endpoints, performs bounded retries, stores candles idempotently, and creates a point-in-time historical ranking. It is research/paper-only and does not place orders.
