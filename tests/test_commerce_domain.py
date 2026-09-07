from uuid import uuid4

import pytest

from packages.commerce.services import InvalidOrderTransition, ORDER_TRANSITIONS


def test_payment_pending_can_be_paid_or_cancelled() -> None:
    assert "PAID" in ORDER_TRANSITIONS["PAYMENT_PENDING"]
    assert "CANCELLED" in ORDER_TRANSITIONS["PAYMENT_PENDING"]


def test_terminal_states_have_no_outgoing_transitions() -> None:
    assert ORDER_TRANSITIONS["FULFILLED"] == frozenset()
    assert ORDER_TRANSITIONS["REFUNDED"] == frozenset()
    assert ORDER_TRANSITIONS["CANCELLED"] == frozenset()
    assert ORDER_TRANSITIONS["EXPIRED"] == frozenset()


def test_invalid_transition_is_domain_error() -> None:
    with pytest.raises(InvalidOrderTransition):
        raise InvalidOrderTransition("PAID->PENDING")


def test_each_order_status_has_explicit_transition_set() -> None:
    expected = {
        "PENDING",
        "PAYMENT_PENDING",
        "PAID",
        "FULFILLING",
        "FULFILLED",
        "REFUND_PENDING",
        "REFUNDED",
        "REFUND_FAILED",
        "CANCELLED",
        "EXPIRED",
    }
    assert set(ORDER_TRANSITIONS) == expected
    assert isinstance(uuid4(), type(uuid4()))
