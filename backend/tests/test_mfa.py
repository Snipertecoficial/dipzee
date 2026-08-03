import base64

from mfa import _code, generate_secret, provisioning_uri, verify_totp


def test_totp_accepts_current_window_and_rejects_wrong_code():
    secret = generate_secret()
    now = 1_700_000_000
    code = _code(secret, now // 30)
    assert verify_totp(secret, code, now=now)
    assert not verify_totp(secret, "000000" if code != "000000" else "111111", now=now)


def test_generated_secret_has_160_bits_and_safe_provisioning_uri():
    secret = generate_secret()
    padded = secret + "=" * ((8 - len(secret) % 8) % 8)
    assert len(base64.b32decode(padded)) == 20
    uri = provisioning_uri(secret, "admin+ops@example.com")
    assert uri.startswith("otpauth://totp/Dipzee%3Aadmin%2Bops%40example.com?")
    assert f"secret={secret}" in uri
