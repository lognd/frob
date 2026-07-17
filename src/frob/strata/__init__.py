"""frob.strata -- the provable system-design language (docs/strata/charter.md).

Phase 0 exposes the kernel: the six-primitive data model the elaborator
targets and the prover consumes. Parser, elaborator, and vocabularies
arrive in later phases (docs/strata/roadmap.md); nothing here may ever
learn a surface vocabulary word (charter law 1).
"""

from __future__ import annotations

from frob.strata._errors import StrataError
from frob.strata._facts import FactBase, build_facts
from frob.strata._models import (
    LABELS,
    TRUST,
    Boundary,
    BoundaryDirection,
    BoundClaim,
    Capacity,
    Claim,
    ClaimBody,
    ClaimResult,
    Flow,
    FlowCondition,
    KernelModel,
    Lattice,
    Metric,
    Node,
    NoFlow,
    Outcome,
    Quantifier,
    Quantity,
    Reach,
    RemoveNode,
    Rewrite,
    Rung,
    ScaleRate,
    Scenario,
    SetTrust,
    Verdict,
)

__all__ = [
    "LABELS",
    "TRUST",
    "Boundary",
    "BoundaryDirection",
    "BoundClaim",
    "Capacity",
    "FactBase",
    "Claim",
    "ClaimBody",
    "ClaimResult",
    "Flow",
    "FlowCondition",
    "KernelModel",
    "Lattice",
    "Metric",
    "Node",
    "NoFlow",
    "Outcome",
    "Quantifier",
    "Quantity",
    "Reach",
    "RemoveNode",
    "Rewrite",
    "Rung",
    "ScaleRate",
    "Scenario",
    "SetTrust",
    "StrataError",
    "Verdict",
    "build_facts",
]
