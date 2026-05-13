"""FastMCP `TokenVerifier` backed by the local SQLite token store."""

from __future__ import annotations

from fastmcp.server.auth.auth import AccessToken, TokenVerifier

from .store import TokenStore


class KrakenTokenVerifier(TokenVerifier):
    """Validate incoming bearer tokens against the local store."""

    def __init__(self, store: TokenStore) -> None:
        super().__init__()
        self._store = store

    async def verify_token(self, token: str) -> AccessToken | None:
        record = self._store.verify(token)
        if record is None:
            return None
        expires_at = int(record.expires_at.timestamp()) if record.expires_at else None
        return AccessToken(
            token=token,
            client_id=record.id,
            scopes=[],
            expires_at=expires_at,
        )
