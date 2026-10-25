"""
app/api/handlers.py
Service entrypoint handlers for batch submission and balance queries.
"""
from typing import Any, Dict
from app.models.primitives import Currency
from app.services.ledger_store import LedgerStore
from app.services.risk_engine import assess_batch_risk


def submit_settlement_batch(
    store: LedgerStore,
    raw_payload: Dict[str, Any],
    max_risk_score: int = 75,
) -> Dict[str, Any]:
    batch = store.load_from_dict(raw_payload)
    assessment = assess_batch_risk(batch, max_allowed_score=max_risk_score)

    if not assessment.approved:
        return {
            "status": "REJECTED",
            "batchId": batch.batch_id,
            "riskScore": assessment.risk_score,
            "flaggedInstructionIds": assessment.flagged_instruction_ids,
        }

    persisted = store.record_batch(assessment.adjusted_batch)
    wire = persisted.to_wire_payload()
    return {
        "status": "SETTLED",
        "batchId": persisted.batch_id,
        "riskScore": assessment.risk_score,
        "flaggedInstructionIds": assessment.flagged_instruction_ids,
        "settlement": wire,
    }


def query_account_summary(
    store: LedgerStore,
    account_id: str,
    currency_code: str = "USD",
) -> Dict[str, Any]:
    currency = Currency(currency_code.upper())
    money = store.get_account_balance(account_id, currency=currency)
    return {
        "accountId": account_id,
        "balance": money.dict(by_alias=True),
        "formattedMajor": str(money.to_major_decimal()),
    }
