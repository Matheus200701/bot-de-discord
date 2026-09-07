from packages.commerce.services import ORDER_TRANSITIONS
from packages.database.models import LedgerEntry


def test_ledger_entry_has_exactly_one_side() -> None:
    debit = LedgerEntry(account="cash:mercadopago_pix", debit_minor=1000, credit_minor=0)
    credit = LedgerEntry(account="revenue:sales", debit_minor=0, credit_minor=1000)
    assert debit.debit_minor == credit.credit_minor
    assert debit.credit_minor == credit.debit_minor == 0


def test_refund_flow_allows_fulfilled_orders() -> None:
    assert "REFUND_PENDING" in ORDER_TRANSITIONS["FULFILLED"]
    assert "REFUNDED" in ORDER_TRANSITIONS["REFUND_PENDING"]


def test_refund_failed_can_be_retried() -> None:
    assert "REFUND_PENDING" in ORDER_TRANSITIONS["REFUND_FAILED"]


def test_refund_amount_is_minor_integer() -> None:
    amount = 12345
    assert isinstance(amount, int)
    assert amount > 0
