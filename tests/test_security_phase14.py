from starlette.testclient import TestClient

from apps.api.security import SecurityMiddleware


def _app(scope, receive, send):
    async def inner():
        while True:
            message = await receive()
            if message.get("type") != "http.request" or not message.get("more_body"):
                break
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    return inner()


def test_trace_is_rejected() -> None:
    client = TestClient(SecurityMiddleware(_app))
    response = client.request("TRACE", "/", headers={"host": "testserver"})
    assert response.status_code == 405
    assert response.text == "method_not_allowed"


def test_trusted_host_allowlist(monkeypatch) -> None:
    monkeypatch.setenv("TRUSTED_HOSTS", "api.example.test")
    client = TestClient(SecurityMiddleware(_app))
    denied = client.get("/", headers={"host": "evil.example.test"})
    allowed = client.get("/", headers={"host": "api.example.test"})
    assert denied.status_code == 400
    assert denied.text == "invalid_host"
    assert allowed.status_code == 200


def test_streamed_body_limit(monkeypatch) -> None:
    monkeypatch.setenv("MAX_REQUEST_BODY_BYTES", "10")
    client = TestClient(SecurityMiddleware(_app))
    response = client.post("/", content=b"x" * 11, headers={"host": "testserver"})
    assert response.status_code == 413
