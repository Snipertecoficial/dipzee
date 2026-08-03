from starlette.responses import Response

import routes_auth


def test_refresh_cookie_is_http_only_strict_and_secure(monkeypatch):
    monkeypatch.setattr(routes_auth, "public_app_url", lambda: "https://dipzee.com")
    response = Response()

    routes_auth._set_refresh_cookie(response, "opaque-refresh-token")

    cookie = response.headers["set-cookie"]
    assert "dz_refresh=opaque-refresh-token" in cookie
    assert "HttpOnly" in cookie
    assert "Secure" in cookie
    assert "SameSite=strict" in cookie
    assert "Path=/api/auth" in cookie


def test_clear_refresh_cookie_uses_same_security_scope(monkeypatch):
    monkeypatch.setattr(routes_auth, "public_app_url", lambda: "https://dipzee.com")
    response = Response()

    routes_auth._clear_refresh_cookie(response)

    cookie = response.headers["set-cookie"]
    assert "dz_refresh=" in cookie
    assert "HttpOnly" in cookie
    assert "Secure" in cookie
    assert "SameSite=strict" in cookie
    assert "Path=/api/auth" in cookie
