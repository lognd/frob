"""Data shapes for frob.fuzz (docs/modules/fuzz.md is authoritative).

Every model is a frozen pydantic ``BaseModel``, matching the posture of
`frob.graph._models` and `frob.gates._models` -- a `FuzzObligation` or
`FuzzResult` is a value compared and cached by identity-of-value, never by
object identity.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict
from typani.error_set import ErrorSet

__all__ = [
    "FuzzEnforce",
    "FuzzError",
    "FuzzObligation",
    "FuzzPolicy",
    "FuzzResult",
]


# frob:doc docs/modules/fuzz.md#public-api
class FuzzEnforce(StrEnum):
    """The `[fuzz].enforce` obligation scope: which symbols owe a fuzz test."""

    OFF = "off"
    INVARIANT_ANCHORED = "invariant-anchored"
    PUBLIC = "public"


# frob:doc docs/modules/fuzz.md#public-api
class FuzzObligation(BaseModel):
    """One symbol's fuzz debt: which ref owes a test and why it is obligated."""

    model_config = ConfigDict(frozen=True)

    ref: str
    reason: str


# frob:doc docs/modules/fuzz.md#public-api
class FuzzResult(BaseModel):
    """One completed fuzz run: examples exercised and the minimal counterexample."""

    model_config = ConfigDict(frozen=True)

    ref: str
    body_digest: str
    examples: int
    falsified: str | None = None


# frob:doc docs/modules/fuzz.md#public-api
class FuzzPolicy(BaseModel):
    """The `[fuzz]` table: obligation scope, per-run budget, rejection ceiling."""

    model_config = ConfigDict(frozen=True)

    enforce: FuzzEnforce = FuzzEnforce.INVARIANT_ANCHORED
    budget_s: int = 60
    max_reject_rate: float = 0.99


# frob:doc docs/modules/fuzz.md#public-api
class FuzzError(ErrorSet):
    """Failure values `resolve`/`run_fuzz`/`stamp_fuzz` can return."""

    NoGenerator = "Type has no derived, declared, or registered strategy"
    RejectionRate = "Derived generator exceeded max_reject_rate"
    StampFailed = "Fuzz stamp read/write failed"
