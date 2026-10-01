from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    jwt_secret: str
    jwt_access_minutes: int = 15
    jwt_refresh_days: int = 7
    cors_origins: str = "http://localhost:3000"


settings = Settings()
