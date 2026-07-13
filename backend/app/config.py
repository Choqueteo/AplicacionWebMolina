from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7   # 7 días = 10 080 min
    # En .env usa formato JSON: ALLOWED_ORIGINS=["http://localhost:5173"]
    allowed_origins: list[str] = ["http://localhost:5173"]
    environment: str = "development"
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    retencion_meses: int = 24

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    @field_validator("database_url", mode="before")
    @classmethod
    def normalizar_database_url(cls, v: str) -> str:
        # Render inyecta postgres://, pero psycopg3 necesita postgresql+psycopg://
        if isinstance(v, str):
            if v.startswith("postgres://"):
                v = v.replace("postgres://", "postgresql+psycopg://", 1)
            elif v.startswith("postgresql://") and "+psycopg" not in v:
                v = v.replace("postgresql://", "postgresql+psycopg://", 1)
        return v


settings = Settings()
