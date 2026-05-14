"""Runtime configuration loaded from environment variables and `.env`."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

KrakenApi = Literal["spot", "futures"]


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

    # Futures keys are issued separately from Spot keys
    # (https://futures.kraken.com/trade/settings/api) and the two are not
    # interchangeable. When `kraken_api="futures"` the server uses these
    # variables; when `kraken_api="spot"` they are ignored.
    kraken_futures_api_key: SecretStr | None = Field(default=None, alias="KRAKEN_FUTURES_API_KEY")
    kraken_futures_api_secret: SecretStr | None = Field(
        default=None, alias="KRAKEN_FUTURES_API_SECRET"
    )

    # Which Kraken product surface to expose. A single instance speaks one
    # API at a time — run two servers if you need both.
    kraken_api: KrakenApi = Field(default="spot", alias="MCP_KRAKEN_API")
    # When `kraken_api="futures"`, point the SDK at the demo environment
    # (https://demo-futures.kraken.com). Has no effect on Spot.
    kraken_futures_sandbox: bool = Field(default=False, alias="MCP_KRAKEN_FUTURES_SANDBOX")
    # Override the Futures base URL (empty string → SDK default, swapped
    # automatically when `kraken_futures_sandbox=True`).
    kraken_futures_base_url: str = Field(default="", alias="KRAKEN_FUTURES_BASE_URL")

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
        """True when credentials for the currently active API are set."""
        if self.kraken_api == "futures":
            return (
                self.kraken_futures_api_key is not None
                and self.kraken_futures_api_secret is not None
            )
        return self.kraken_api_key is not None and self.kraken_api_secret is not None

    def active_credentials(self) -> tuple[SecretStr | None, SecretStr | None]:
        """Return the (key, secret) pair for the currently active API."""
        if self.kraken_api == "futures":
            return self.kraken_futures_api_key, self.kraken_futures_api_secret
        return self.kraken_api_key, self.kraken_api_secret


def load_settings() -> Settings:
    return Settings()
