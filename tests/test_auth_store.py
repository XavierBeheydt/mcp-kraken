"""Tests for the bearer-token store."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from mcp_kraken.auth import TokenStore, generate_token, hash_token


def test_generate_token_has_prefix_and_entropy() -> None:
    a = generate_token()
    b = generate_token()
    assert a.startswith("mck_")
    assert a != b
    assert len(a) > 30


def test_create_and_verify_roundtrip(store: TokenStore) -> None:
    issued = store.create(name="alice")
    assert issued.plaintext.startswith("mck_")

    record = store.verify(issued.plaintext)
    assert record is not None
    assert record.id == issued.record.id
    assert record.name == "alice"
    assert record.is_active


def test_unknown_token_returns_none(store: TokenStore) -> None:
    assert store.verify("mck_does-not-exist") is None


def test_revoke(store: TokenStore) -> None:
    issued = store.create(name="bob")
    assert store.revoke(issued.record.id) is True
    assert store.verify(issued.plaintext) is None
    # Idempotent: second revoke is a no-op
    assert store.revoke(issued.record.id) is False


def test_expired_token_is_rejected(store: TokenStore) -> None:
    past = datetime.now(UTC) - timedelta(seconds=1)
    issued = store.create(name="expired", expires_at=past)
    assert store.verify(issued.plaintext) is None


def test_list_orders_newest_first(store: TokenStore) -> None:
    a = store.create(name="a")
    b = store.create(name="b")
    listed = [r.id for r in store.list()]
    assert listed[0] == b.record.id
    assert listed[1] == a.record.id


def test_list_filters_revoked(store: TokenStore) -> None:
    keep = store.create(name="keep")
    drop = store.create(name="drop")
    store.revoke(drop.record.id)
    active = [r.id for r in store.list(include_revoked=False)]
    assert keep.record.id in active
    assert drop.record.id not in active


def test_hash_is_stable() -> None:
    assert hash_token("mck_abc") == hash_token("mck_abc")
    assert hash_token("mck_abc") != hash_token("mck_def")


def test_verify_updates_last_used(store: TokenStore) -> None:
    issued = store.create(name="ping")
    assert issued.record.last_used_at is None
    store.verify(issued.plaintext)
    record = store.get(issued.record.id)
    assert record is not None
    assert record.last_used_at is not None
