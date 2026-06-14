from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    # En .env usa formato JSON: ALLOWED_ORIGINS=["http://localhost:5173"]
    allowed_origins: list[str] = ["http://localhost:5173"]
    environment: str = "development"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
