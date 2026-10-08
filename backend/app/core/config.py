from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    jwt_secret: str
    jwt_access_minutes: int = 15
    jwt_refresh_days: int = 7
    cors_origins: str = "http://localhost:3000"

    # Supabase Auth: SOMENTE identidade (quem é o usuário). Os dados do usuário ficam no PostgreSQL.
    # SUPABASE_URL é obrigatória: dela saem o emissor (iss) esperado e o endereço do JWKS.
    supabase_url: str = ""
    # Só é necessário se o projeto Supabase ainda assina os tokens com o segredo legado (HS256).
    # Projetos com "JWT Signing Keys" (ES256/RS256) NÃO precisam dela. Nunca coloque em NEXT_PUBLIC_*.
    supabase_jwt_secret: str = ""

    @field_validator("supabase_url", "supabase_jwt_secret", mode="before")
    @classmethod
    def _limpar(cls, valor: object) -> object:
        # .env salvo com CRLF (Windows) ou com espaços sobrando quebraria a validação do emissor.
        return valor.strip() if isinstance(valor, str) else valor


settings = Settings()