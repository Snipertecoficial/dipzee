import asyncio

import refresh_tokens
from tests.fakedb import FakeDB


def _run(coro):
    return asyncio.run(coro)


def test_replay_revokes_only_the_compromised_token_family(monkeypatch):
    fake_db = FakeDB()
    monkeypatch.setattr(refresh_tokens, "db", fake_db)

    first_device = _run(refresh_tokens.issue("u1", mfa_verified=True))
    other_device = _run(refresh_tokens.issue("u1", mfa_verified=True))
    rotated = _run(refresh_tokens.rotate(first_device))
    assert rotated is not None
    _, successor, mfa_verified = rotated
    assert mfa_verified is True

    # Replaying the old credential invalidates its successor chain, but must
    # not turn a stolen/expired token into a logout-all primitive.
    assert _run(refresh_tokens.rotate(first_device)) is None
    assert _run(refresh_tokens.rotate(successor)) is None
    assert _run(refresh_tokens.rotate(other_device)) is not None
