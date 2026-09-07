from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class PaymentIntent:
    provider_payment_id: str
    status: str
    amount_minor: int
    currency: str
    checkout_url: str | None = None
    qr_code: str | None = None
    qr_code_text: str | None = None

class PaymentProvider(ABC):
    name: str

    @abstractmethod
    async def create_payment(self, *, order_id: str, amount_minor: int, currency: str, metadata: dict[str, str]) -> PaymentIntent: ...

    @abstractmethod
    async def get_payment(self, provider_payment_id: str) -> PaymentIntent: ...

    @abstractmethod
    async def cancel_payment(self, provider_payment_id: str) -> None: ...

    @abstractmethod
    async def refund_payment(self, provider_payment_id: str, amount_minor: int | None = None) -> None: ...

    @abstractmethod
    async def validate_webhook(self, headers: dict[str, str], raw_body: bytes) -> bool: ...

    @abstractmethod
    async def parse_webhook_event(self, raw_body: bytes) -> dict[str, Any]: ...
