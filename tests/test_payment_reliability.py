from datetime import datetime, timedelta, timezone

from packages.payments.reliability import CircuitBreaker, exponential_backoff, next_reconcile_time


def test_exponential_backoff_is_capped() -> None:
    assert 2 <= exponential_backoff(1, 2, 10) < 3
    assert 8 <= exponential_backoff(3, 2, 10) < 9
    assert 10 <= exponential_backoff(20, 2, 10) <= 11


def test_circuit_breaker_opens_and_recovers() -> None:
    breaker = CircuitBreaker(failure_threshold=2, recovery_seconds=1)
    assert breaker.allow("mp")
    breaker.failure("mp")
    assert breaker.allow("mp")
    breaker.failure("mp")
    assert not breaker.allow("mp")
    breaker.opened_at["mp"] = datetime.now(timezone.utc) - timedelta(seconds=2)
    assert breaker.allow("mp")


def test_terminal_payment_never_schedules_reconciliation() -> None:
    assert next_reconcile_time("approved") is None
    assert next_reconcile_time("cancelled") is None
    assert next_reconcile_time("rejected") is None
    assert next_reconcile_time("expired") is None
    assert next_reconcile_time("waiting_payment") is not None
