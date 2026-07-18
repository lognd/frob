"""frob.strata -- the provable system-design language (docs/strata/charter.md).

Phase 0 exposes the kernel: the six-primitive data model the elaborator
targets and the prover consumes. Parser, elaborator, and vocabularies
arrive in later phases (docs/strata/roadmap.md); nothing here may ever
learn a surface vocabulary word (charter law 1).
"""

from __future__ import annotations

from frob.strata._ast import (
    AtCallRequire,
    BalancerDecl,
    BoundaryDecl,
    CacheDecl,
    CdnDecl,
    ClaimDecl,
    ConfineUse,
    FlowDecl,
    ForbidCall,
    ForbidImport,
    Mediate,
    Module,
    NodeDecl,
    PolicyDecl,
    PolicyRule,
    QueueDecl,
    RefineDecl,
    ScopeSpec,
    StoreDecl,
)
from frob.strata._ast import (
    Capacity as SurfaceCapacity,
)
from frob.strata._claims import evaluate_claims
from frob.strata._elaborate import elaborate
from frob.strata._errors import StrataError
from frob.strata._facts import FactBase, build_facts
from frob.strata._infra import InfraExpansion, elaborate_infra
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
from frob.strata._packs import ANALYZABLE, ANALYZABLE_POLICY_ID, require_analyzable
from frob.strata._parse import parse_module
from frob.strata._policy import CompiledPolicies, CompiledPolicy, compile_policies
from frob.strata._report import render_report, summarize

__all__ = [
    "ANALYZABLE",
    "ANALYZABLE_POLICY_ID",
    "LABELS",
    "TRUST",
    "AtCallRequire",
    "BalancerDecl",
    "Boundary",
    "BoundaryDecl",
    "BoundaryDirection",
    "BoundClaim",
    "CacheDecl",
    "Capacity",
    "CdnDecl",
    "ClaimDecl",
    "CompiledPolicies",
    "CompiledPolicy",
    "ConfineUse",
    "FactBase",
    "Claim",
    "ClaimBody",
    "ClaimResult",
    "Flow",
    "FlowCondition",
    "FlowDecl",
    "ForbidCall",
    "ForbidImport",
    "InfraExpansion",
    "KernelModel",
    "Lattice",
    "Mediate",
    "Metric",
    "Module",
    "Node",
    "NodeDecl",
    "NoFlow",
    "Outcome",
    "PolicyDecl",
    "PolicyRule",
    "Quantifier",
    "Quantity",
    "QueueDecl",
    "Reach",
    "RefineDecl",
    "RemoveNode",
    "Rewrite",
    "Rung",
    "ScaleRate",
    "Scenario",
    "ScopeSpec",
    "SetTrust",
    "StoreDecl",
    "StrataError",
    "SurfaceCapacity",
    "Verdict",
    "build_facts",
    "compile_policies",
    "elaborate",
    "elaborate_infra",
    "evaluate_claims",
    "parse_module",
    "render_report",
    "require_analyzable",
    "summarize",
]
