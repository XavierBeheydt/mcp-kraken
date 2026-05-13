"""Bearer token primitives.

Tokens are opaque random strings, never reversibly stored. The on-disk store
keeps only a SHA-256 hash plus the first few bytes (`token_id`) as a
human-friendly identifier for listing and revocation.
"""

from __future__ import annotations

import hashlib
import secrets

TOKEN_PREFIX = "mck_"
TOKEN_BYTES = 32  # 256 bits of entropy
TOKEN_ID_LEN = 12  # short prefix shown in `token list`


def generate_token() -> str:
    """Generate a fresh opaque bearer token."""
    return f"{TOKEN_PREFIX}{secrets.token_urlsafe(TOKEN_BYTES)}"


def hash_token(token: str) -> str:
    """Hash a token for storage. SHA-256 is appropriate for high-entropy secrets."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def token_id_from_secret(token: str) -> str:
    """Derive a short, non-secret identifier from the full token.

    The id is a stable function of the token, so it can be re-derived when the
    operator supplies the token at revocation time.
    """
    return hash_token(token)[:TOKEN_ID_LEN]
