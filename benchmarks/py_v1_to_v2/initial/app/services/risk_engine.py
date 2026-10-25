"""
app/services/risk_engine.py
Risk evaluation engine using legacy Pydantic v1 .copy(update=...), __fields__, and untyped helpers.
"""
from typing import Dict, List, Tuple
from pydantic import BaseModel, Field

from app.models.primitives import Money
from app.models.transactions import SettlementBatch, SettlementInstruction


class RiskAssessment(BaseModel):
    batch_id: str = Field(..., alias="batchId")
    risk_score: int = Field(..., alias="riskScore", ge=0, le=100)
    flagged_instruction_ids: List[str] = Field(default_factory=list, alias="flaggedInstructionIds")
    approved: bool
    adjusted_batch: SettlementBatch = Field(..., alias="adjustedBatch")

    class Config:
        allow_population_by_field_name = True


def evaluate_instruction_risk(inst: SettlementInstruction) -> Tuple[int, SettlementInstruction]:
    score = 0
    cross_border = inst.source.country_iso != inst.destination.country_iso
    if cross_border:
        score += 25

    if inst.amount.amount_cents >= 1_000_000:
        score += 35
    elif inst.amount.amount_cents >= 250_000:
        score += 15

    if "high-risk" in inst.tags or "crypto" in inst.tags:
        score += 30

    # If cross-border and fee_bps < 50, bump fee_bps to 50 and add 'cross-border-surcharge' tag
    updated_inst = inst
    if cross_border and inst.fee_bps < 50:
        new_tags = list(inst.tags)
        if "cross-border-surcharge" not in new_tags:
            new_tags.append("cross-border-surcharge")
        updated_inst = inst.copy(update={"fee_bps": 50, "tags": new_tags})

    return min(score, 100), updated_inst


def assess_batch_risk(batch: SettlementBatch, max_allowed_score: int = 75) -> RiskAssessment:
    # Inspect model fields using legacy v1 __fields__ attribute
    required_fields = list(SettlementBatch.__fields__.keys())
    if "instructions" not in required_fields:
        raise RuntimeError("Invalid batch schema")

    adjusted_instructions: List[SettlementInstruction] = []
    flagged_ids: List[str] = []
    max_score = 0

    for inst in batch.instructions:
        inst_score, updated_inst = evaluate_instruction_risk(inst)
        adjusted_instructions.append(updated_inst)
        if inst_score > max_score:
            max_score = inst_score
        if inst_score >= 50:
            flagged_ids.append(inst.instruction_id)

    adjusted_batch = batch.copy(update={"instructions": adjusted_instructions})
    approved = max_score <= max_allowed_score

    return RiskAssessment(
        batch_id=batch.batch_id,
        risk_score=max_score,
        flagged_instruction_ids=flagged_ids,
        approved=approved,
        adjusted_batch=adjusted_batch,
    )
