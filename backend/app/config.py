from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv_if_present(env_path: Path) -> None:
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


_load_dotenv_if_present(BACKEND_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    app_env: str
    host: str
    port: int
    catalog_version: str
    llm_provider: str
    llm_api_key: str
    llm_model: str
    llm_timeout_sec: float
    llm_max_retries: int
    database_path: Path

    @classmethod
    def from_env(cls) -> "Settings":
        db_raw = os.getenv("DATABASE_PATH", str(BACKEND_DIR / "data" / "bookmood.db"))
        db_path = Path(db_raw)
        if not db_path.is_absolute():
            db_path = (BACKEND_DIR / db_path).resolve()

        return cls(
            app_env=os.getenv("APP_ENV", "development"),
            host=os.getenv("HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", "8000")),
            catalog_version=os.getenv("CATALOG_VERSION", "v1"),
            llm_provider=os.getenv("LLM_PROVIDER", "mock").lower(),
            llm_api_key=os.getenv("LLM_API_KEY", ""),
            llm_model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            llm_timeout_sec=float(os.getenv("LLM_TIMEOUT_SEC", "8.0")),
            llm_max_retries=int(os.getenv("LLM_MAX_RETRIES", "1")),
            database_path=db_path,
        )

