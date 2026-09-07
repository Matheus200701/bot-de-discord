from __future__ import annotations

import os
import secrets

from starlette.types import ASGIApp, Message, Receive, Scope, Send


class RequestTooLarge(Exception):
    """Raised internally when a streamed HTTP request exceeds the configured limit."""


class SecurityMiddleware:
    """ASGI hardening layer with request-size, host, method and CSRF controls."""

    ALLOWED_METHODS = {"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"}
    UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.max_body_bytes = int(os.getenv("MAX_REQUEST_BODY_BYTES", str(2 * 1024 * 1024)))
        self.trusted_hosts = {
            host.strip().lower()
            for host in os.getenv("TRUSTED_HOSTS", "").split(",")
            if host.strip()
        }

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = str(scope.get("method", "")).upper()
        if method not in self.ALLOWED_METHODS:
            await self._simple_response(send, 405, b"method_not_allowed")
            return

        headers = {k.lower(): v for k, v in scope.get("headers", [])}
        host = headers.get(b"host", b"").decode("latin-1").split(":", 1)[0].lower()
        if self.trusted_hosts and host not in self.trusted_hosts:
            await self._simple_response(send, 400, b"invalid_host")
            return

        if method in self.UNSAFE_METHODS:
            cookie_header = headers.get(b"cookie", b"").decode("latin-1")
            if "commerce_session=" in cookie_header:
                cookies = {
                    item.split("=", 1)[0].strip(): item.split("=", 1)[1].strip()
                    for item in cookie_header.split(";")
                    if "=" in item
                }
                csrf_cookie = cookies.get("commerce_csrf", "")
                csrf_header = headers.get(b"x-csrf-token", b"").decode("latin-1")
                if not csrf_cookie or not csrf_header or not secrets.compare_digest(csrf_cookie, csrf_header):
                    await self._simple_response(send, 403, b"csrf_failed")
                    return

        content_length = headers.get(b"content-length")
        if content_length:
            try:
                if int(content_length) > self.max_body_bytes:
                    await self._simple_response(send, 413, b"request_too_large")
                    return
            except ValueError:
                await self._simple_response(send, 400, b"invalid_content_length")
                return

        request_id = headers.get(b"x-request-id", b"").decode("ascii", "ignore")
        if len(request_id) > 128 or not request_id:
            request_id = secrets.token_hex(16)

        received = 0
        response_started = False

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] != "http.request":
                return message
            body = message.get("body", b"")
            received += len(body)
            if received > self.max_body_bytes:
                raise RequestTooLarge
            return message

        async def send_with_security(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
                response_headers = list(message.get("headers", []))
                response_headers.extend(
                    [
                        (b"x-request-id", request_id.encode("ascii")),
                        (b"x-content-type-options", b"nosniff"),
                        (b"x-frame-options", b"DENY"),
                        (b"referrer-policy", b"no-referrer"),
                        (b"permissions-policy", b"camera=(), microphone=(), geolocation=()"),
                        (b"content-security-policy", b"default-src 'none'; frame-ancestors 'none'"),
                    ]
                )
                if os.getenv("ENFORCE_HSTS", "false").lower() == "true":
                    response_headers.append(
                        (b"strict-transport-security", b"max-age=31536000; includeSubDomains")
                    )
                message = {**message, "headers": response_headers}
            await send(message)

        try:
            await self.app(scope, limited_receive, send_with_security)
        except RequestTooLarge:
            if not response_started:
                await self._simple_response(send, 413, b"request_too_large")

    @staticmethod
    async def _simple_response(send: Send, status: int, body: bytes) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [
                    (b"content-type", b"text/plain"),
                    (b"content-length", str(len(body)).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})
