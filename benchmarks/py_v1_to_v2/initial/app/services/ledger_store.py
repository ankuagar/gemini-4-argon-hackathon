"""
app/services/ledger_store.py
In-memory ledger store using deprecated .json(), .parse_raw(), .parse_obj(), and untyped methods.
"""
from typing import Any, Dict, List, Optional
from app.models.primitives import Currency, Money
from app.models.transactions import SettlementBatch


class LedgerStore:
    def __init__(self):
        self._batches_by_id: Dict[str, str] = {}
        self._idempotency_index: Dict[str, str] = {}
        self._account_balances: Dict[str, int] = {}

    def record_batch(self, batch: SettlementBatch) -> SettlementBatch:
        existing_batch_id = self._idempotency_index.get(batch.idempotency_key)
        if existing_batch_id is not None:
            raw_json = self._batches_by_id[existing_batch_id]
            return SettlementBatch.parse_raw(raw_json)

        # Serialize with legacy Pydantic v1 .json(by_alias=True)
        serialized = batch.json(by_alias=True)
        self._batches_by_id[batch.batch_id] = serialized
        self._idempotency_index[batch.idempotency_key] = batch.batch_id

        for inst in batch.instructions:
            src_id = inst.source.account_id
            dst_id = inst.destination.account_id
            gross = inst.amount.amount_cents
            net = inst.net_settlement_amount().amount_cents
            self._account_balances[src_id] = self._account_balances.get(src_id, 0) - gross
            self._account_balances[dst_id] = self._account_balances.get(dst_id, 0) + net

        return SettlementBatch.parse_raw(serialized)

    def get_batch(self, batch_id: str) -> Optional[SettlementBatch]:
        raw_json = self._batches_by_id.get(batch_id)
        if raw_json is None:
            return None
        return SettlementBatch.parse_raw(raw_json)

    def load_from_dict(self, payload: Dict[str, Any]) -> SettlementBatch:
        return SettlementBatch.parse_obj(payload)

    def get_account_balance(self, account_id: str, currency: Currency = Currency.USD) -> Money:
        cents = self._account_balances.get(account_id, 0)
        return Money.parse_obj({"amountCents": cents, "currency": currency.value})
