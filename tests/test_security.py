from __future__ import annotations

import asyncio

from starlette.testclient import TestClient

from apps.api.security import SecurityMiddleware


def test_security_headers_and_request_id() -> None:
    async def app(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": [(b"content-type", b"text/plain")]})
        await send({"type": "http.response.body", "body": b"ok"})

    client = TestClient(SecurityMiddleware(app))
    response = client.get("/", headers={"host": "testserver"})

    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["x-request-id"]


def test_security_middleware_rejects_oversized_content_length(monkeypatch) -> None:
    monkeypatch.setenv("MAX_REQUEST_BODY_BYTES", "10")

    async def app(scope, receive, send):
        raise AssertionError("application should not be reached")

    client = TestClient(SecurityMiddleware(app))
    response = client.post("/", headers={"host": "testserver", "content-length": "11"}, content=b"x")

    assert response.status_code == 413
    assert response.text == "request_too_large"


def test_security_middleware_rejects_streamed_oversize(monkeypatch) -> None:
    monkeypatch.setenv("MAX_REQUEST_BODY_BYTES", "3")
    sent: list[dict] = []
    messages = iter(
        [
            {"type": "http.request", "body": b"ab", "more_body": True},
            {"type": "http.request", "body": b"cd", "more_body": False},
        ]
    )

    async def app(scope, receive, send):
        await receive()
        await receive()

    async def receive():
        return next(messages)

    async def send(message):
        sent.append(message)

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "headers": [(b"host", b"testserver")],
        "query_string": b"",
        "scheme": "http",
        "http_version": "1.1",
    }
    asyncio.run(SecurityMiddleware(app)(scope, receive, send))

    assert sent[0]["status"] == 413
    assert sent[1]["body"] == b"request_too_large"


def test_security_middleware_rejects_unsupported_method() -> None:
    async def app(scope, receive, send):
        raise AssertionError("application should not be reached")

    client = TestClient(SecurityMiddleware(app))
    response = client.request("TRACE", "/", headers={"host": "testserver"})

    assert response.status_code == 405
    assert response.text == "method_not_allowed"
