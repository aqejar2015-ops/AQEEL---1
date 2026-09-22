from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    binance_base_url: str = os.getenv("BINANCE_BASE_URL", "https://api.binance.com")
    db_path: str = os.getenv("DB_PATH", "data/market_data.db")
    request_timeout: float = float(os.getenv("REQUEST_TIMEOUT", "15"))
    max_retries: int = int(os.getenv("MAX_RETRIES", "5"))
    retry_delay_seconds: float = float(os.getenv("RETRY_DELAY_SECONDS", "1"))
    request_limit: int = int(os.getenv("BINANCE_REQUEST_LIMIT", "1000"))


settings = Settings()
