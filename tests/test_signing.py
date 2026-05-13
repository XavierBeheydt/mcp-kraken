"""Signing tests against the reference vector documented by Kraken.

Source: <https://docs.kraken.com/api/docs/guides/spot-rest-auth>
"""

from __future__ import annotations

from mcp_kraken.kraken.signing import next_nonce, sign


def test_next_nonce_is_monotonic() -> None:
    a = next_nonce()
    b = next_nonce()
    assert b >= a


def test_sign_kraken_reference_vector() -> None:
    """Kraken's documented example.

    api_secret = "kQH5HW/8p1uGOVjbgWA7FunAmGO8lsSUXNsu3eow76sz84Q18fWxnyRzBHCd3pd5nE9qa99HAZtuZuj6F1huXg=="
    url_path   = "/0/private/AddOrder"
    post_data  = nonce=1616492376594&ordertype=limit&pair=XBTUSD&price=37500&type=buy&volume=1.25
    expected   = 4/dpxb3iT4tp/ZCVEwSnEsLxx0bqyhLpdfOpc6fn7OR8+UClSV5n9E6aSS8MPtnRfp32bAb0nmbRn6H8ndwLUQ==
    """
    api_secret = (
        "kQH5HW/8p1uGOVjbgWA7FunAmGO8lsSUXNsu3eow76sz84Q18fWxnyRzBHCd3pd5nE9qa99HAZtuZuj6F1huXg=="
    )
    url_path = "/0/private/AddOrder"
    post_data = {
        "nonce": "1616492376594",
        "ordertype": "limit",
        "pair": "XBTUSD",
        "price": "37500",
        "type": "buy",
        "volume": "1.25",
    }

    signature = sign(url_path, post_data, api_secret)
    assert signature == (
        "4/dpxb3iT4tp/ZCVEwSnEsLxx0bqyhLpdfOpc6fn7OR8+UClSV5n9E6aSS8MPtnRfp32bAb0nmbRn6H8ndwLUQ=="
    )
