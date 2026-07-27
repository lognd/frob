"""REL22x reliability family: RETRY backoff+jitter, non-idempotent-op
guard, and IDEMPOTENCY key obligation (T-0641, child of the T-0331
systems-checks epic, docs/strata/reliability.md), mirroring `_reliability.
py`'s REL2xx TIMEOUT structure (module docstring precedent, T-0699/T-0640:
one rule module per obligation, same `Report`/`Violation` pydantic pair,
registration in `_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES`, CLI wiring
via `frob.app.sys_runner`).

THREE RULES, all flow-scoped (a node can originate several retryable
flows, so each fires per-flow -- `MULTI_INSTANCE_WAIVER_FAMILIES`
discipline, same as REL200/REL201):

  - REL220 missing backoff/jitter: a flow marked `retry` (this hop is
    retried on failure) with no `backoff_jitter` attr declared. Deny-by-
    default (T-0331 catalog: a naive retry with no backoff/jitter is a
    retry-storm risk -- every failure mode `_lint.py` LINT003's surge
    obligation already worries about at the scenario level, but here at
    the per-flow declaration level).
  - REL221 non-idempotent retry with no idempotency key: a flow marked
    `retry` whose DESTINATION node is neither `idempotent`
    (`_models.py::_IDEMPOTENT`, the same marker `_facts.py`'s at-least-
    once delivery join already reuses) nor `idempotency_key` (a narrower
    marker: the op is not naturally idempotent, but the CALLER attaches a
    dedup key so a retried mutating call is made safe). Retrying a
    non-idempotent mutating op with neither marker risks a duplicate
    side-effect on every retry -- deny-by-default.
  - REL222 unproven backoff: a flow declares `backoff_jitter`, but the
    PROVABILITY CONSTRAINT (T-0331, non-negotiable, same discipline
    REL201 established) forbids discharging by bare declaration alone --
    at least one of the flow's ENDPOINTS must have bound code
    (`_obligation_proof.py::node_has_bound_code`) containing a real
    backoff/jitter-shaped token. A flow with NEITHER endpoint bound to any
    code at all is UNCHECKABLE -- honestly silent, the same ceiling REL201
    draws.

GRAMMAR-DATA CEILING, HONESTLY: like REL200/REL201's `timeout` attr,
`retry`/`backoff_jitter` are bare Flow attrs (no numeric magnitude --
`strata-core/src/parse.rs`'s generic `attr KEY=VALUE` clause only lexes an
identifier VALUE, not a digit-led literal), so REL220/REL222 prove
PRESENCE of a caller-declared backoff/jitter obligation and its code-level
evidence, not a specific bound count/multiplier -- the exact ceiling
`_reliability.py`'s module docstring already discloses for `timeout`.
`idempotency_key` is likewise a bare NODE marker (presence-only, no actual
key name round-trips through the grammar) -- same ceiling, no strata-core
change needed (this ticket's scope is `src/frob/strata/**`/
`docs/strata/**`/`tests/unit/strata/**` only, same as T-0640's).
"""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: this file's 'only' hits \
# are source-level design-rationale/scope-cut prose mirroring _reliability.py's own \
# identical waiver for the identical reason (module docstring precedent, T-0641), not \
# a separate cross-module contract"

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict
from typani.result import Err, Ok, Result

from frob.logging import get_logger

from ._code_binding import bind_code
from ._errors import StrataError
from ._models import KernelModel
from ._obligation_proof import bound_endpoints, files_evidence_token, owner_index
from ._waive import apply_waivers

_log = get_logger(__name__)

#: `frob sys audit` rule id for REL220 missing backoff/jitter: a `retry`
#: flow with no `backoff_jitter` attr declared.
# frob:doc docs/strata/reliability.md#rel22x-retry-obligation-t-0641
REL_MISSING_BACKOFF = "REL220"

#: `frob sys audit` rule id for REL221 non-idempotent retry: a `retry` flow
#: whose dst is neither `idempotent` nor `idempotency_key`.
# frob:doc docs/strata/reliability.md#rel22x-retry-obligation-t-0641
REL_NONIDEMPOTENT_RETRY = "REL221"

#: `frob sys audit` rule id for REL222 unproven backoff: a flow declares
#: `backoff_jitter`, but its bound endpoint code has no real backoff/
#: jitter-shaped token (PROVABILITY CONSTRAINT, T-0331).
# frob:doc docs/strata/reliability.md#rel22x-retry-obligation-t-0641
REL_UNPROVEN_BACKOFF = "REL222"

#: Every REL22x rule id this module can emit -- used by `_apply_retry_
#: waivers`' `in_scope` (this module's own, narrow family; T-0644's
#: `_reliability.py` docstring documents the real regression a SHARED
#: superset caused elsewhere in this family, so this module keeps its own
#: dedicated family constant rather than importing a wider one).
# frob:doc docs/strata/reliability.md#rel22x-retry-obligation-t-0641
RETRY_RULES: frozenset[str] = frozenset(
    {REL_MISSING_BACKOFF, REL_NONIDEMPOTENT_RETRY, REL_UNPROVEN_BACKOFF}
)

#: Flow attr marking a hop retried on failure -- the population REL220/
#: REL221/REL222 apply to; flows with no `retry` marker are out of scope
#: entirely (a one-shot flow has no retry-storm/dup-effect risk to guard).
_RETRY_ATTR = "retry"

#: Flow attr discharging the REL220 backoff/jitter obligation (presence-
#: only, module docstring's grammar-data ceiling).
_BACKOFF_JITTER_ATTR = "backoff_jitter"

#: Node attr marking a naturally-idempotent op (`_models.py::_IDEMPOTENT`'s
#: exact string, kept as a local literal copy for the same import-
#: isolation reason `_reliability.py::_UNIT_ATTR` keeps its own copy of
#: `_host.py`'s markers -- this module does not import `_models.py`'s
#: private module-level constant).
_IDEMPOTENT_ATTR = "idempotent"

#: Node attr marking a mutating op made safe under retry via a caller-
#: attached dedup key (narrower than `idempotent`: the op itself is NOT
#: naturally idempotent, but a key discharges the duplicate-effect risk).
_IDEMPOTENCY_KEY_ATTR = "idempotency_key"

#: Regex proving a real backoff/jitter-shaped token in bound source text
#: (REL222) -- deliberately narrow (a syntactic token scan, not a semantic
#: call-argument binding), matching common retry-library/backoff-loop
#: shapes: `backoff=`/`jitter=` kwargs, `exponential_backoff(`, or a
#: `tenacity`/`backoff` decorator call. Same honesty line
#: `_reliability.py::_TIMEOUT_TOKEN_RE`'s docstring already establishes:
#: not a claim the matched token bounds the SAME retry the flow models,
#: only that the originating node's bound code contains real evidence of
#: a backoff/jitter construct.
_BACKOFF_TOKEN_RE = re.compile(
    r"(\bbackoff\s*=|\bjitter\s*=|exponential_backoff|@retry\(|\btenacity\b)",
    re.IGNORECASE,
)


# frob:doc docs/strata/reliability.md#rel22x-retry-obligation-t-0641
class RetryViolation(BaseModel):
    """One REL22x finding: rule id, the reporting node (the flow's `src`,
    the caller who owes the retry obligation), a human-readable detail,
    and `sub_target` (always the flow id -- every REL22x rule is flow-
    scoped). Mirrors `_reliability.py::ReliabilityViolation`'s shape."""

    model_config = ConfigDict(frozen=True)

    rule: str
    node: str
    detail: str
    sub_target: str | None = None


# frob:doc docs/strata/reliability.md#rel22x-retry-obligation-t-0641
class RetryReport(BaseModel):
    """Every UNWAIVED REL22x finding, plus `waived` (T-0174 channel, kept
    for report visibility, never silently dropped). Mirrors
    `_reliability.py::ReliabilityReport`'s shape."""

    model_config = ConfigDict(frozen=True)

    violations: tuple[RetryViolation, ...] = ()
    waived: tuple[RetryViolation, ...] = ()


def _is_retry_flow(attrs: tuple[str, ...]) -> bool:
    """Whether a flow's `attrs` carries the bare `retry` marker."""
    return _RETRY_ATTR in attrs


def _has_backoff_jitter(attrs: tuple[str, ...]) -> bool:
    """Whether a flow's `attrs` carries the bare `backoff_jitter` marker."""
    return _BACKOFF_JITTER_ATTR in attrs


def _dst_is_safe_under_retry(dst_attrs: tuple[str, ...]) -> bool:
    """Whether a flow's destination node declares itself safe to retry
    (naturally idempotent, or a caller-attached idempotency key)."""
    return _IDEMPOTENT_ATTR in dst_attrs or _IDEMPOTENCY_KEY_ATTR in dst_attrs


def _missing_backoff_violations(model: KernelModel) -> list[RetryViolation]:
    """REL220: every `retry` flow with no `backoff_jitter` attr."""
    violations: list[RetryViolation] = []
    for flow in model.flows:
        if not _is_retry_flow(flow.attrs) or _has_backoff_jitter(flow.attrs):
            continue
        _log.warning(
            "retry: REL220 flow %s (%s -> %s) retries with no backoff/jitter",
            flow.id,
            flow.src,
            flow.dst,
        )
        violations.append(
            RetryViolation(
                rule=REL_MISSING_BACKOFF,
                node=flow.src,
                sub_target=flow.id,
                detail=(
                    f"flow {flow.id} ({flow.src} -> {flow.dst}) is marked retry "
                    "with no backoff/jitter obligation (no `backoff_jitter` attr)"
                ),
            )
        )
    return violations


def _nodes_by_id(model: KernelModel) -> dict[str, tuple[str, ...]]:
    """Node id -> its `attrs`, once -- REL221's dst-lookup needs this per
    flow rather than a linear `model.nodes` scan per flow."""
    return {node.id: node.attrs for node in model.nodes}


def _nonidempotent_retry_violations(model: KernelModel) -> list[RetryViolation]:
    """REL221: every `retry` flow whose dst is neither `idempotent` nor
    `idempotency_key` -- a retried mutating op with neither marker risks a
    duplicate side-effect on every retry."""
    violations: list[RetryViolation] = []
    node_attrs = _nodes_by_id(model)
    for flow in model.flows:
        if not _is_retry_flow(flow.attrs):
            continue
        dst_attrs = node_attrs.get(flow.dst, ())
        if _dst_is_safe_under_retry(dst_attrs):
            continue
        _log.warning(
            "retry: REL221 flow %s retries non-idempotent dst %s with no "
            "idempotency key",
            flow.id,
            flow.dst,
        )
        violations.append(
            RetryViolation(
                rule=REL_NONIDEMPOTENT_RETRY,
                node=flow.src,
                sub_target=flow.id,
                detail=(
                    f"flow {flow.id} ({flow.src} -> {flow.dst}) retries a "
                    f"non-idempotent op at {flow.dst} with no idempotency key "
                    "(dst has neither `idempotent` nor `idempotency_key`)"
                ),
            )
        )
    return violations


def _unproven_backoff_violations(
    model: KernelModel, owner_by_node: dict[str, list[str]], root: Path
) -> list[RetryViolation]:
    """REL222: every `retry` flow declaring `backoff_jitter` where at least
    one endpoint has bound code, but none of the bound endpoints' code
    carries a real backoff/jitter-shaped token (PROVABILITY CONSTRAINT).
    Mirrors `_reliability.py::_unproven_timeout_violations` exactly,
    parameterized on `_BACKOFF_TOKEN_RE`."""
    violations: list[RetryViolation] = []
    for flow in model.flows:
        if not _is_retry_flow(flow.attrs) or not _has_backoff_jitter(flow.attrs):
            continue
        endpoints = bound_endpoints(flow.src, flow.dst, owner_by_node)
        if not endpoints:
            continue
        if any(
            files_evidence_token(owner_by_node[node], root, _BACKOFF_TOKEN_RE)
            for node in endpoints
        ):
            continue
        reporting_node = endpoints[0]
        _log.warning(
            "retry: REL222 flow %s declares backoff_jitter but bound "
            "endpoint(s) %s have no real backoff/jitter token",
            flow.id,
            endpoints,
        )
        violations.append(
            RetryViolation(
                rule=REL_UNPROVEN_BACKOFF,
                node=reporting_node,
                sub_target=flow.id,
                detail=(
                    f"flow {flow.id} declares backoff_jitter, but bound "
                    f"endpoint(s) {endpoints}'s code has no real backoff/jitter "
                    "token (proof-against-code, T-0331 PROVABILITY CONSTRAINT)"
                ),
            )
        )
    return violations


def _apply_retry_waivers(model: KernelModel, violations: list[RetryViolation]):  # noqa: ANN201
    """Apply every node's `waive` clause to `violations` (T-0174), exactly
    `_reliability.py::_apply_reliability_waivers`'s pattern reused for the
    REL22x family."""
    return apply_waivers(
        model,
        violations,
        rule_of=lambda v: v.rule,
        target_of=lambda v: v.node,
        sub_target_of=lambda v: v.sub_target,
        in_scope=lambda rule: rule in RETRY_RULES,
    )


# frob:doc docs/strata/reliability.md#rel22x-retry-obligation-t-0641
# frob:ticket T-0641
# frob:ticket T-0958
# frob:enforces SDC-4-IDEMPOTENCY
# frob:enforces SDC-5-RETRY-BACKOFF-JITTER
# frob:tests tests/unit/strata/test_retry.py::TestMissingBackoff.test_retry_flow_without_backoff_fires  # noqa: E501
def check_retry_obligations(
    model: KernelModel, root: Path
) -> Result[RetryReport, StrataError]:
    """The REL22x RETRY-obligation entrypoint (T-0641): REL220 (missing
    backoff/jitter), REL221 (non-idempotent retry with no idempotency
    key), and REL222 (declared-but-unproven backoff, proof-against-code)
    across every flow in `model`, waivers already applied. `root` is the
    repo root `_code_binding.py::bind_code` binds against -- `Err`
    propagates `bind_code`'s `AmbiguousCodeBinding` unchanged (deny by
    default, the same discipline `check_reliability_timeouts` uses)."""
    bound = bind_code(model, root)
    if bound.is_err:
        return Err(bound.danger_err)
    owner_by_node = owner_index(bound.danger_ok.owner)

    violations: list[RetryViolation] = []
    violations.extend(_missing_backoff_violations(model))
    violations.extend(_nonidempotent_retry_violations(model))
    violations.extend(_unproven_backoff_violations(model, owner_by_node, root))
    applied = _apply_retry_waivers(model, violations)
    waived = tuple(wf.finding for wf in applied.waived)
    stale = tuple(
        RetryViolation(
            rule="RELWAIVE002",
            node=stale_waiver.node,
            sub_target=stale_waiver.rule,
            detail=(
                f"waive {stale_waiver.rule!r} on node {stale_waiver.node} "
                f"reason={stale_waiver.reason!r} is stale -- no matching "
                f"finding fired this run"
            ),
        )
        for stale_waiver in applied.stale
    )
    _log.info(
        "retry: %d violation(s), %d waived, %d stale waiver(s)",
        len(applied.kept) + len(stale),
        len(waived),
        len(applied.stale),
    )
    return Ok(RetryReport(violations=tuple(applied.kept) + stale, waived=waived))


__all__ = [
    "REL_MISSING_BACKOFF",
    "REL_NONIDEMPOTENT_RETRY",
    "REL_UNPROVEN_BACKOFF",
    "RETRY_RULES",
    "RetryReport",
    "RetryViolation",
    "check_retry_obligations",
]
