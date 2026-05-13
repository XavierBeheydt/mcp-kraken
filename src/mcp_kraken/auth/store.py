"""SQLite-backed store for issued bearer tokens.

Only token hashes are persisted. The plaintext token is shown once at
creation time and cannot be recovered.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .tokens import generate_token, hash_token, token_id_from_secret

_SCHEMA = """
CREATE TABLE IF NOT EXISTS tokens (
    id           TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    token_hash   TEXT NOT NULL UNIQUE,
    created_at   TEXT NOT NULL,
    expires_at   TEXT,
    revoked_at   TEXT,
    last_used_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_tokens_hash ON tokens (token_hash);
"""


@dataclass(frozen=True)
class TokenRecord:
    """A token's metadata as stored on disk (no secret material)."""

    id: str
    name: str
    created_at: datetime
    expires_at: datetime | None
    revoked_at: datetime | None
    last_used_at: datetime | None

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None

    @property
    def is_expired(self) -> bool:
        return self.expires_at is not None and datetime.now(UTC) >= self.expires_at

    @property
    def is_active(self) -> bool:
        return not self.is_revoked and not self.is_expired


@dataclass(frozen=True)
class IssuedToken:
    """A freshly minted token. The plaintext is only available here, once."""

    record: TokenRecord
    plaintext: str


class TokenStore:
    """Thin SQLite wrapper. Safe to instantiate per call; cheap."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
        finally:
            conn.close()

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> TokenRecord:
        def _parse(v: str | None) -> datetime | None:
            return datetime.fromisoformat(v) if v else None

        created = datetime.fromisoformat(row["created_at"])
        return TokenRecord(
            id=row["id"],
            name=row["name"],
            created_at=created,
            expires_at=_parse(row["expires_at"]),
            revoked_at=_parse(row["revoked_at"]),
            last_used_at=_parse(row["last_used_at"]),
        )

    def create(self, name: str, expires_at: datetime | None = None) -> IssuedToken:
        """Mint a new token. Returns plaintext once; only the hash is stored."""
        plaintext = generate_token()
        token_hash = hash_token(plaintext)
        token_id = token_id_from_secret(plaintext)
        now = datetime.now(UTC).isoformat()
        exp = expires_at.isoformat() if expires_at else None
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO tokens (id, name, token_hash, created_at, expires_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (token_id, name, token_hash, now, exp),
            )
            row = conn.execute("SELECT * FROM tokens WHERE id = ?", (token_id,)).fetchone()
        return IssuedToken(record=self._row_to_record(row), plaintext=plaintext)

    def list(self, *, include_revoked: bool = True) -> list[TokenRecord]:
        with self._connect() as conn:
            sql = "SELECT * FROM tokens"
            if not include_revoked:
                sql += " WHERE revoked_at IS NULL"
            sql += " ORDER BY created_at DESC"
            rows = conn.execute(sql).fetchall()
        return [self._row_to_record(r) for r in rows]

    def get(self, token_id: str) -> TokenRecord | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM tokens WHERE id = ?", (token_id,)).fetchone()
        return self._row_to_record(row) if row else None

    def revoke(self, token_id: str) -> bool:
        """Mark a token as revoked. Returns True if it was active before."""
        now = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE tokens SET revoked_at = ? WHERE id = ? AND revoked_at IS NULL",
                (now, token_id),
            )
            return cur.rowcount > 0

    def verify(self, plaintext: str) -> TokenRecord | None:
        """Look up a token by its plaintext value.

        Returns the record if the token exists, is not revoked, and not expired.
        Otherwise returns None. Updates `last_used_at` on success.
        """
        token_hash = hash_token(plaintext)
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM tokens WHERE token_hash = ?", (token_hash,)
            ).fetchone()
            if row is None:
                return None
            record = self._row_to_record(row)
            if not record.is_active:
                return None
            conn.execute(
                "UPDATE tokens SET last_used_at = ? WHERE id = ?",
                (datetime.now(UTC).isoformat(), record.id),
            )
        return record
