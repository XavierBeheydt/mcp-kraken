"""Runtime configuration loaded from environment variables and `.env`."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings.

    Values come from environment variables (prefixed `MCP_KRAKEN_` except
    Kraken credentials which use their conventional names) and from a `.env`
    file in the working directory if present.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    kraken_api_key: SecretStr | None = Field(default=None, alias="KRAKEN_API_KEY")
    kraken_api_secret: SecretStr | None = Field(default=None, alias="KRAKEN_API_SECRET")
    kraken_base_url: str = Field(
        default="https://api.kraken.com",
        alias="KRAKEN_BASE_URL",
    )

    host: str = Field(default="0.0.0.0", alias="MCP_KRAKEN_HOST")  # noqa: S104
    port: int = Field(default=8765, alias="MCP_KRAKEN_PORT")
    path: str = Field(default="/mcp", alias="MCP_KRAKEN_PATH")

    token_db: Path = Field(default=Path("./data/tokens.db"), alias="MCP_KRAKEN_TOKEN_DB")
    auth_disabled: bool = Field(default=False, alias="MCP_KRAKEN_AUTH_DISABLED")

    # TLS — when both paths are set the HTTP server speaks HTTPS instead.
    ssl_keyfile: Path | None = Field(default=None, alias="MCP_KRAKEN_SSL_KEYFILE")
    ssl_certfile: Path | None = Field(default=None, alias="MCP_KRAKEN_SSL_CERTFILE")

    http_timeout: float = Field(default=30.0, alias="MCP_KRAKEN_HTTP_TIMEOUT")
    log_level: str = Field(default="INFO", alias="MCP_KRAKEN_LOG_LEVEL")

    def have_kraken_credentials(self) -> bool:
        return self.kraken_api_key is not None and self.kraken_api_secret is not None


def load_settings() -> Settings:
    return Settings()
