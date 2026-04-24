from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///data/b2b_growth.db")
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    wechat_appid: str | None = os.getenv("WECHAT_APPID")
    wechat_secret: str | None = os.getenv("WECHAT_APPSECRET")


settings = Settings()
