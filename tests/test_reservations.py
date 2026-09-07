from datetime import datetime, timedelta, timezone

from packages.commerce.services import ORDER_TRANSITIONS
from packages.commerce.reservations import reservation_expiry


def test_reservation_expiry_is_in_the_future() -> None:
    before = datetime.now(timezone.utc)
    expires = reservation_expiry(60)
    assert expires > before
    assert expires <= before + timedelta(seconds=61)


def test_terminal_order_states_have_no_outgoing_transitions() -> None:
    for status in ("FULFILLED", "REFUNDED", "CANCELLED", "EXPIRED"):
        assert ORDER_TRANSITIONS[status] == frozenset()
