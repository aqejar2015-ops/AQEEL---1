from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class Settings:
    project_name: str = "Crypto Intelligence & Opportunity Engine"
    app_env: str = os.getenv("CIOE_ENV", "dev")
    data_dir: str = os.getenv("CIOE_DATA_DIR", str(Path("data").resolve()))
    logs_dir: str = os.getenv("CIOE_LOGS_DIR", str(Path("logs").resolve()))
    db_path: str = os.getenv("CIOE_DB_PATH", str(Path("data") / "cioe.db"))
    binance_base_url: str = os.getenv("BINANCE_BASE_URL", "https://api.binance.com")
    binance_ws_url: str = os.getenv("BINANCE_WS_URL", "wss://stream.binance.com:9443")
    analysis_interval_seconds: int = int(os.getenv("ANALYSIS_INTERVAL_SECONDS", "120"))
    selected_coin_count: int = int(os.getenv("SELECTED_COIN_COUNT", "7"))
    historical_days: int = int(os.getenv("HISTORICAL_DAYS", "30"))
    simulation_capital: float = float(os.getenv("SIMULATION_CAPITAL", "1000"))
    default_fee_bps: float = float(os.getenv("DEFAULT_FEE_BPS", "10"))
    max_retries: int = int(os.getenv("MAX_RETRIES", "5"))
    retry_backoff_seconds: float = float(os.getenv("RETRY_BACKOFF_SECONDS", "1.5"))
    request_timeout_seconds: float = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "15"))

    @property
    def data_dir_path(self) -> Path:
        return Path(self.data_dir)

    @property
    def logs_dir_path(self) -> Path:
        return Path(self.logs_dir)


settings = Settings()
