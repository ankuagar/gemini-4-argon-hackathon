"""
app/models/transactions.py
Legacy Pydantic v1 transaction and batch models using @root_validator, each_item=True, and .dict().
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, validator, root_validator

from app.models.primitives import AccountRef, Currency, Money


class SettlementInstruction(BaseModel):
    instruction_id: str = Field(..., alias="instructionId", regex=r"^TX-[0-9]{4,10}$")
    source: AccountRef
    destination: AccountRef
    amount: Money
    fee_bps: int = Field(default=25, alias="feeBps", ge=0, le=2500)
    tags: List[str] = Field(default_factory=list)
    memo: Optional[str] = None

    class Config:
        allow_population_by_field_name = True

    @validator("tags", each_item=True, pre=True)
    def clean_each_tag(cls, v):
        if not isinstance(v, str):
            raise ValueError("Each tag must be a string")
        cleaned = v.strip().lower()
        if not cleaned:
            raise ValueError("Tag cannot be empty")
        return cleaned

    @root_validator
    def validate_transfer_parties(cls, values):
        src = values.get("source")
        dst = values.get("destination")
        amt = values.get("amount")
        if src and dst and src.account_id == dst.account_id:
            raise ValueError("source and destination account_id cannot be identical")
        if amt and amt.amount_cents <= 0:
            raise ValueError("Transfer amount_cents must be strictly positive")
        return values

    def compute_fee(self) -> Money:
        fee_cents = (self.amount.amount_cents * self.fee_bps + 5000) // 10000
        return Money(amount_cents=fee_cents, currency=self.amount.currency)

    def net_settlement_amount(self) -> Money:
        fee = self.compute_fee()
        return Money(
            amount_cents=self.amount.amount_cents - fee.amount_cents,
            currency=self.amount.currency,
        )


class SettlementBatch(BaseModel):
    batch_id: str = Field(..., alias="batchId", regex=r"^BATCH-[A-Z0-9-]+$")
    settlement_currency: Currency = Field(..., alias="settlementCurrency")
    instructions: List[SettlementInstruction]
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        alias="createdAt",
    )
    idempotency_key: str = Field(..., alias="idempotencyKey", min_length=8)

    class Config:
        allow_population_by_field_name = True

    @root_validator
    def validate_batch_consistency(cls, values):
        curr = values.get("settlement_currency")
        items = values.get("instructions") or []
        if not items:
            raise ValueError("SettlementBatch must contain at least one instruction")
        seen_ids = set()
        for inst in items:
            if inst.amount.currency != curr:
                raise ValueError(
                    f"Instruction {inst.instruction_id} currency {inst.amount.currency} "
                    f"does not match batch currency {curr}"
                )
            if inst.instruction_id in seen_ids:
                raise ValueError(f"Duplicate instruction_id in batch: {inst.instruction_id}")
            seen_ids.add(inst.instruction_id)
        return values

    def total_gross(self) -> Money:
        total = sum(i.amount.amount_cents for i in self.instructions)
        return Money(amount_cents=total, currency=self.settlement_currency)

    def total_fees(self) -> Money:
        total = sum(i.compute_fee().amount_cents for i in self.instructions)
        return Money(amount_cents=total, currency=self.settlement_currency)

    def total_net(self) -> Money:
        total = sum(i.net_settlement_amount().amount_cents for i in self.instructions)
        return Money(amount_cents=total, currency=self.settlement_currency)

    def to_wire_payload(self) -> Dict[str, Any]:
        data = self.dict(by_alias=True)
        data["totalGrossCents"] = self.total_gross().amount_cents
        data["totalFeeCents"] = self.total_fees().amount_cents
        data["totalNetCents"] = self.total_net().amount_cents
        return data
