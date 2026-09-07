from starlette.testclient import TestClient

from apps.api.security import SecurityMiddleware


async def _app(scope, receive, send):
    await send({"type": "http.response.start", "status": 204, "headers": []})
    await send({"type": "http.response.body", "body": b""})


def test_cookie_authenticated_mutation_requires_csrf() -> None:
    client = TestClient(SecurityMiddleware(_app))
    denied = client.post("/api/v1/auth/discord/logout", headers={"host": "testserver", "cookie": "commerce_session=session; commerce_csrf=abc"})
    allowed = client.post("/api/v1/auth/discord/logout", headers={"host": "testserver", "cookie": "commerce_session=session; commerce_csrf=abc", "x-csrf-token": "abc"})
    assert denied.status_code == 403
    assert denied.text == "csrf_failed"
    assert allowed.status_code == 204
