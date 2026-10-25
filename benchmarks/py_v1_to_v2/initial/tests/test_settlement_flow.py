"""
tests/test_settlement_flow.py
Comprehensive test suite verifying validation, alias serialization, risk adjustments, idempotency, and balances.
Must pass under `pytest -W error` (zero Pydantic v2 deprecation warnings!) and `mypy --strict app`.
"""
from decimal import Decimal
import pytest
from pydantic import ValidationError

from app.models.primitives import AccountRef, Currency, Money
from app.models.transactions import SettlementBatch, SettlementInstruction
from app.services.ledger_store import LedgerStore
from app.services.risk_engine import assess_batch_risk
from app.api.handlers import query_account_summary, submit_settlement_batch


def test_money_validation_and_arithmetic() -> None:
    m1 = Money(amountCents="1050.4", currency="usd")  # type: ignore[arg-type]
    assert m1.amount_cents == 1050
    assert m1.currency == Currency.USD
    assert m1.to_major_decimal() == Decimal("10.50")

    m2 = Money(amount_cents=450, currency=Currency.USD)
    m3 = m1.add(m2)
    assert m3.amount_cents == 1500

    jpy = Money(amount_cents=500, currency=Currency.JPY)
    assert jpy.to_major_decimal() == Decimal("500")
    with pytest.raises(ValueError, match="Currency mismatch"):
        m1.add(jpy)


def test_account_ref_whitespace_and_routing_rules() -> None:
    acc = AccountRef(
        accountId="  ACC-998877  ",
        routingCode="US001122",
        holderName="  Ada Lovelace ",
        countryIso="us",
    )
    assert acc.account_id == "ACC-998877"
    assert acc.holder_name == "Ada Lovelace"
    assert acc.country_iso == "US"
    assert acc.to_public_dict()["accountId"] == "ACC-998877"

    with pytest.raises(ValidationError):
        AccountRef(
            accountId="ACC-998877",
            routingCode="GB998877",  # Invalid for US country_iso
            holderName="Ada",
            countryIso="US",
        )


def test_instruction_tags_and_self_transfer_rejection() -> None:
    src = AccountRef(accountId="ACC-111111", routingCode="US1234", holderName="Alice", countryIso="US")
    dst = AccountRef(accountId="ACC-222222", routingCode="DE9988", holderName="Bob", countryIso="DE")

    inst = SettlementInstruction(
        instructionId="TX-1001",
        source=src,
        destination=dst,
        amount=Money(amount_cents=100_000, currency=Currency.USD),
        feeBps=20,
        tags=["  Urgent ", "VIP"],
    )
    assert inst.tags == ["urgent", "vip"]
    assert inst.compute_fee().amount_cents == 200
    assert inst.net_settlement_amount().amount_cents == 99_800

    with pytest.raises(ValidationError, match="cannot be identical"):
        SettlementInstruction(
            instructionId="TX-1002",
            source=src,
            destination=src,
            amount=Money(amount_cents=5000, currency=Currency.USD),
        )


def test_end_to_end_settlement_and_cross_border_surcharge() -> None:
    store = LedgerStore()
    payload = {
        "batchId": "BATCH-2026-01",
        "settlementCurrency": "USD",
        "idempotencyKey": "idem-key-0001",
        "instructions": [
            {
                "instructionId": "TX-5001",
                "source": {
                    "accountId": "ACC-100001",
                    "routingCode": "US1111",
                    "holderName": "Sender Corp",
                    "countryIso": "US",
                },
                "destination": {
                    "accountId": "ACC-200002",
                    "routingCode": "GB2222",
                    "holderName": "Receiver Ltd",
                    "countryIso": "GB",
                },
                "amount": {"amountCents": 300_000, "currency": "USD"},
                "feeBps": 10,
                "tags": ["Vendor"],
            }
        ],
    }

    res = submit_settlement_batch(store, payload, max_risk_score=75)
    assert res["status"] == "SETTLED"
    # Cross-border (25) + >=250k (15) = 40 risk score
    assert res["riskScore"] == 40
    # Cross-border surcharge bumped feeBps from 10 to 50 -> 0.50% of 300,000 = 1,500 cents
    assert res["settlement"]["totalGrossCents"] == 300_000
    assert res["settlement"]["totalFeeCents"] == 1_500
    assert res["settlement"]["totalNetCents"] == 298_500

    # Idempotent replay should not double-debit
    replay = submit_settlement_batch(store, payload, max_risk_score=75)
    assert replay["status"] == "SETTLED"

    sender_summary = query_account_summary(store, "ACC-100001", "USD")
    receiver_summary = query_account_summary(store, "ACC-200002", "USD")
    assert sender_summary["balance"]["amountCents"] == -300_000
    assert receiver_summary["balance"]["amountCents"] == 298_500
    assert receiver_summary["formattedMajor"] == "2985.00"


def test_high_risk_batch_rejected() -> None:
    store = LedgerStore()
    payload = {
        "batchId": "BATCH-2026-99",
        "settlementCurrency": "USD",
        "idempotencyKey": "idem-key-9999",
        "instructions": [
            {
                "instructionId": "TX-9001",
                "source": {
                    "accountId": "ACC-100001",
                    "routingCode": "US1111",
                    "holderName": "Sender Corp",
                    "countryIso": "US",
                },
                "destination": {
                    "accountId": "ACC-300003",
                    "routingCode": "FR3333",
                    "holderName": "Offshore LLC",
                    "countryIso": "FR",
                },
                "amount": {"amountCents": 2_000_000, "currency": "USD"},
                "tags": ["crypto", "high-risk"],
            }
        ],
    }

    res = submit_settlement_batch(store, payload, max_risk_score=75)
    assert res["status"] == "REJECTED"
    assert res["riskScore"] == 90
    assert res["flaggedInstructionIds"] == ["TX-9001"]
