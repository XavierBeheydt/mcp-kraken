"""Kraken request signing.

The signature scheme is documented at
<https://docs.kraken.com/api/docs/guides/spot-rest-auth>:

    HMAC-SHA512(
        key    = base64_decode(api_secret),
        message= url_path_bytes
                 + sha256(nonce_str + urlencoded_post_body).digest()
    )

The result is base64-encoded and placed in the `API-Sign` header. The
`API-Key` header holds the public API key. Every private call also includes
a strictly-increasing integer `nonce` in the POST body.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import time
from collections.abc import Mapping
from urllib.parse import urlencode


def next_nonce() -> int:
    """Return a strictly increasing nonce based on the system clock.

    Microsecond resolution is fine in practice — Kraken accepts any integer
    that is greater than the previous one for that key.
    """
    return int(time.time() * 1_000_000)


def sign(url_path: str, post_data: Mapping[str, object], api_secret: str) -> str:
    """Compute the `API-Sign` header value.

    `post_data` must already contain the `nonce` field. `url_path` is the
    full request path (e.g. ``/0/private/Balance``), not just the endpoint
    name.
    """
    encoded = urlencode(post_data).encode("utf-8")
    nonce = str(post_data["nonce"]).encode("utf-8")
    message = url_path.encode("utf-8") + hashlib.sha256(nonce + encoded).digest()
    mac = hmac.new(base64.b64decode(api_secret), message, hashlib.sha512)
    return base64.b64encode(mac.digest()).decode("utf-8")
