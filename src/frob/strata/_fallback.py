"""REL24x reliability family: FALLBACK/graceful-degradation obligation for
CRITICAL dependencies (T-0643, child of the T-0331 systems-checks epic,
docs/strata/reliability.md), mirroring `_circuit_breaker.py`'s REL23x
structure (module docstring precedent, T-0699/T-0640/T-0641/T-0642: one
rule module per obligation, same `Report`/`Violation` pydantic pair,
node-scoped single-instance waiver carve-out, CLI wiring via
`frob.app.sys_runner`). Reuses `_circuit_breaker.py`'s dependency-
criticality classification (`is_critical_dependency`/`CRITICAL_ATTR`)
rather than re-deriving it -- the reason this ticket is `blocked_by`
T-0642: the `critical` marker's population is exactly the one T-0642
already defined.

TWO RULES, both NODE-scoped (a node has at most one `critical` marker and
fires at most one REL240/REL241 finding each -- single-instance-per-node,
the same carve-out REL210/REL211/REL230/REL231 already establish, NOT
registered in `MULTI_INSTANCE_WAIVER_FAMILIES`):

  - REL240 missing fallback: a node marked `critical` (via
    `_circuit_breaker.py::is_critical_dependency`) with no `fallback`
    attr declared. Deny-by-default: an unguarded call into a CRITICAL
    dependency with no degraded-mode path risks a full outage the moment
    that dependency fails, not just a slow/expensive call.
  - REL241 unproven fallback: a node DOES declare `fallback`, but the
    T-0331 PROVABILITY CONSTRAINT forbids discharging it by bare
    declaration alone -- the node must have at least one file bound to
    it (`_obligation_proof.py::node_has_bound_code`) containing a real
    fallback/graceful-degradation-shaped token. A node with no bound
    code at all is UNCHECKABLE, not unproven -- the same ceiling
    REL201/REL222/REL231 draw.

GRAMMAR-DATA CEILING, HONESTLY: `fallback` is a bare Node attr (no
numeric magnitude -- the same digit-led-literal ceiling every other
REL2xx marker in this family discloses), so REL240/REL241 prove PRESENCE
of a declared fallback obligation and its code-level evidence, not a
specific degraded-mode behavior. No `strata-core` change needed (this
ticket's scope is `src/frob/strata/**`/`docs/strata/**`/
`tests/unit/strata/**` only, same as T-0640/T-0641/T-0642's).
"""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict
from typani.result import Err, Ok, Result

from frob.logging import get_logger

from ._circuit_breaker import is_critical_dependency
from ._code_binding import bind_code
from ._errors import StrataError
from ._models import KernelModel
from ._obligation_proof import files_evidence_token, node_has_bound_code, owner_index
from ._waive import apply_waivers, stale_relwaive_violations

_log = get_logger(__name__)

#: `frob sys audit` rule id for REL240 missing fallback: a `critical` node
#: with no `fallback` attr declared.
# frob:doc \
# docs/strata/reliability.md#rel24x-fallbackgraceful-degradation-obligation-t-0643
REL_MISSING_FALLBACK = "REL240"

#: `frob sys audit` rule id for REL241 unproven fallback: a node declares
#: `fallback`, but its bound code has no real fallback/graceful-
#: degradation-shaped token (PROVABILITY CONSTRAINT, T-0331).
# frob:doc \
# docs/strata/reliability.md#rel24x-fallbackgraceful-degradation-obligation-t-0643
REL_UNPROVEN_FALLBACK = "REL241"

#: Every REL24x rule id this module can emit -- this module's own, narrow
#: family for `_apply_fallback_waivers`' `in_scope` (the same "never a
#: shared superset" discipline `_reliability.py`'s module docstring
#: documents the real regression for).
# frob:doc \
# docs/strata/reliability.md#rel24x-fallbackgraceful-degradation-obligation-t-0643
FALLBACK_RULES: frozenset[str] = frozenset(
    {REL_MISSING_FALLBACK, REL_UNPROVEN_FALLBACK}
)

#: Node attr discharging the REL240 fallback obligation (presence-only,
#: module docstring's grammar-data ceiling).
_FALLBACK_ATTR = "fallback"

#: Regex proving a real fallback/graceful-degradation-shaped token in
#: bound source text (REL241) -- deliberately narrow (a syntactic token
#: scan, not a semantic call-argument binding), matching common fallback
#: shapes: a `fallback`/`degrade(d)`/`graceful_degrad` identifier, or an
#: `except`-guarded call returning a cached/default/stale value. Same
#: honesty line `_reliability.py::_TIMEOUT_TOKEN_RE`'s docstring already
#: establishes: not a claim the matched token guards the SAME call the
#: node models, only that the node's bound code contains real evidence of
#: a fallback/degraded-mode construct.
_FALLBACK_TOKEN_RE = re.compile(
    r"(\bfallback\b|graceful_degrad|\bdegraded\b|\bdegrade\(|"
    r"cached_default|stale_(?:cache|value|read))",
    re.IGNORECASE,
)


# frob:doc \
# docs/strata/reliability.md#rel24x-fallbackgraceful-degradation-obligation-t-0643
class FallbackViolation(BaseModel):
    """One REL24x finding: rule id, the node, a human-readable detail.
    `sub_target` stays `None` -- single-instance-per-node (module
    docstring: at most one `critical` marker, at most one REL240/REL241
    finding each), the same bare-rule waiver carve-out REL210/REL211/
    REL230/REL231 use. Mirrors `_circuit_breaker.py::
    CircuitBreakerViolation`'s shape."""

    model_config = ConfigDict(frozen=True)

    rule: str
    node: str
    detail: str
    sub_target: str | None = None


# frob:doc \
# docs/strata/reliability.md#rel24x-fallbackgraceful-degradation-obligation-t-0643
class FallbackReport(BaseModel):
    """Every UNWAIVED REL24x finding, plus `waived` (T-0174 channel, kept
    for report visibility, never silently dropped). Mirrors
    `_circuit_breaker.py::CircuitBreakerReport`'s shape."""

    model_config = ConfigDict(frozen=True)

    violations: tuple[FallbackViolation, ...] = ()
    waived: tuple[FallbackViolation, ...] = ()


def _has_fallback(attrs: tuple[str, ...]) -> bool:
    """Whether a node's `attrs` carries the bare `fallback` marker."""
    return _FALLBACK_ATTR in attrs


def _missing_fallback_violations(model: KernelModel) -> list[FallbackViolation]:
    """REL240: every `critical` node with no `fallback` attr."""
    violations: list[FallbackViolation] = []
    for node in model.nodes:
        if not is_critical_dependency(node.attrs) or _has_fallback(node.attrs):
            continue
        _log.warning(
            "fallback: REL240 node %s is a critical dependency with no "
            "fallback/graceful-degradation path",
            node.id,
        )
        violations.append(
            FallbackViolation(
                rule=REL_MISSING_FALLBACK,
                node=node.id,
                detail=(
                    f"node {node.id} is marked critical with no fallback/"
                    "graceful-degradation obligation (no `fallback` attr)"
                ),
            )
        )
    return violations


def _unproven_fallback_violations(
    model: KernelModel, owner_by_node: dict[str, list[str]], root: Path
) -> list[FallbackViolation]:
    """REL241: every node declaring `fallback` with bound code but no real
    fallback/graceful-degradation-shaped token in it (PROVABILITY
    CONSTRAINT). A node with no bound code at all is skipped --
    uncheckable, not unproven (module docstring, same ceiling
    REL201/REL222/REL231 draw)."""
    violations: list[FallbackViolation] = []
    for node in model.nodes:
        if not _has_fallback(node.attrs):
            continue
        if not node_has_bound_code(node.id, owner_by_node):
            continue
        if files_evidence_token(owner_by_node[node.id], root, _FALLBACK_TOKEN_RE):
            continue
        _log.warning(
            "fallback: REL241 node %s declares fallback but its bound code "
            "has no real fallback/graceful-degradation token",
            node.id,
        )
        violations.append(
            FallbackViolation(
                rule=REL_UNPROVEN_FALLBACK,
                node=node.id,
                detail=(
                    f"node {node.id} declares fallback, but its bound code "
                    "has no real fallback/graceful-degradation token "
                    "(proof-against-code, T-0331 PROVABILITY CONSTRAINT)"
                ),
            )
        )
    return violations


def _apply_fallback_waivers(model: KernelModel, violations: list[FallbackViolation]):  # noqa: ANN201
    """Apply every node's `waive` clause to `violations` (T-0174), exactly
    `_circuit_breaker.py::_apply_circuit_breaker_waivers`'s pattern reused
    for the REL24x family."""
    return apply_waivers(
        model,
        violations,
        rule_of=lambda v: v.rule,
        target_of=lambda v: v.node,
        sub_target_of=lambda v: v.sub_target,
        in_scope=lambda rule: rule in FALLBACK_RULES,
    )


# frob:doc \
# docs/strata/reliability.md#rel24x-fallbackgraceful-degradation-obligation-t-0643
# frob:ticket T-0643
# frob:enforces CHK-GATE-REL240
# frob:enforces CHK-GATE-REL241
# frob:tests tests/unit/strata/test_fallback.py::TestMissingFallback.test_critical_node_without_fallback_fires  # noqa: E501
def check_fallback_obligations(
    model: KernelModel, root: Path
) -> Result[FallbackReport, StrataError]:
    """The REL24x FALLBACK-obligation entrypoint (T-0643): REL240 (missing
    fallback/graceful-degradation) and REL241 (declared-but-unproven,
    proof-against-code) across every `critical` node in `model`, waivers
    already applied. `root` is the repo root `_code_binding.py::bind_code`
    binds against -- `Err` propagates `bind_code`'s `AmbiguousCodeBinding`
    unchanged (deny by default, the same discipline
    `check_circuit_breaker_obligations` uses)."""
    bound = bind_code(model, root)
    if bound.is_err:
        return Err(bound.danger_err)
    owner_by_node = owner_index(bound.danger_ok.owner)

    violations: list[FallbackViolation] = []
    violations.extend(_missing_fallback_violations(model))
    violations.extend(_unproven_fallback_violations(model, owner_by_node, root))
    applied = _apply_fallback_waivers(model, violations)
    waived = tuple(wf.finding for wf in applied.waived)
    stale = stale_relwaive_violations(applied.stale, FallbackViolation)
    _log.info(
        "fallback: %d violation(s), %d waived, %d stale waiver(s)",
        len(applied.kept) + len(stale),
        len(waived),
        len(applied.stale),
    )
    return Ok(FallbackReport(violations=tuple(applied.kept) + stale, waived=waived))


__all__ = [
    "FALLBACK_RULES",
    "REL_MISSING_FALLBACK",
    "REL_UNPROVEN_FALLBACK",
    "FallbackReport",
    "FallbackViolation",
    "check_fallback_obligations",
]
