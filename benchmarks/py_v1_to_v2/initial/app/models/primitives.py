"""
app/models/primitives.py
Legacy Pydantic v1 primitives with deprecated validators, Config class, and missing strict type annotations.
"""
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, validator, root_validator


class Currency(str, Enum):
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"


class Money(BaseModel):
    amount_cents: int = Field(..., alias="amountCents", description="Amount in minor units")
    currency: Currency = Field(default=Currency.USD)

    class Config:
        allow_population_by_field_name = True
        frozen = True
        schema_extra = {
            "example": {"amountCents": 12500, "currency": "USD"}
        }

    @validator("amount_cents", pre=True)
    def parse_amount(cls, v):
        if isinstance(v, (float, str, Decimal)):
            dec = Decimal(str(v)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
            return int(dec)
        if not isinstance(v, int):
            raise ValueError("amount_cents must be an integer or numeric string")
        return v

    @validator("currency", pre=True)
    def normalize_currency(cls, v):
        if isinstance(v, str):
            return v.strip().upper()
        return v

    def to_major_decimal(self):
        exponent = Decimal("1") if self.currency == Currency.JPY else Decimal("0.01")
        return (Decimal(self.amount_cents) * exponent).quantize(exponent)

    def add(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError(f"Currency mismatch: {self.currency} vs {other.currency}")
        return self.copy(update={"amount_cents": self.amount_cents + other.amount_cents})


class AccountRef(BaseModel):
    account_id: str = Field(..., alias="accountId", regex=r"^ACC-[A-Z0-9]{6,12}$")
    routing_code: str = Field(..., alias="routingCode", min_length=4, max_length=16)
    holder_name: str = Field(..., alias="holderName")
    country_iso: str = Field(default="US", alias="countryIso")

    class Config:
        allow_population_by_field_name = True
        anystr_strip_whitespace = True

    @root_validator
    def check_country_and_routing(cls, values):
        country = values.get("country_iso", "US")
        routing = values.get("routing_code", "")
        if len(country) != 2 or not country.isalpha():
            raise ValueError("country_iso must be a 2-letter ISO code")
        values["country_iso"] = country.upper()
        if values["country_iso"] == "US" and not routing.startswith("US"):
            raise ValueError("US accounts must have a routingCode starting with 'US'")
        return values

    def to_public_dict(self) -> Dict[str, Any]:
        return self.dict(by_alias=True)
