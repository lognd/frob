"""REL2xx reliability family: TIMEOUT obligation on every remote/cross-
boundary flow (T-0640, child of the T-0331 systems-checks epic,
docs/strata/reliability.md).

Every `Flow` in the kernel model already IS a cross-boundary movement by
definition (`_models.py::Flow`'s docstring: "directed movement of
anything between two nodes") -- there is no in-process/self-flow
construct in this grammar, so this module treats every flow as an
unbounded-hang risk unless it is explicitly discharged or exempted.
Mirrors `_contention.py`'s SYS2xx shape deliberately (module docstring
precedent, T-0699): a rule module, a `Report`/`Violation` pydantic pair,
registration in `_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES` (a node can
originate more than one flow, so each fires per-flow), and CLI wiring
via `frob.app.sys_runner`.

TWO RULES:

  - REL200 missing timeout: a flow with no `timeout` attr declared and no
    exemption (`async` -- fire-and-forget, the SAME bare-marker
    convention `_crash.py`'s no-hang check already uses for queue
    consumers; or `local` -- explicitly declared as not crossing a real
    process/service boundary). Deny-by-default (T-0331 catalog: "TIMEOUT
    on every remote/cross-boundary flow -- unbounded hang otherwise").
  - REL201 unproven timeout: a flow DOES declare `timeout`, but the
    PROVABILITY CONSTRAINT (T-0331, non-negotiable) forbids discharging
    an obligation by bare declaration alone -- at least one of the flow's
    ENDPOINTS (`flow.src` OR `flow.dst`) must have bound code
    (`_code_binding.py::bind_code`) containing a real `timeout=`-shaped
    token (T-0758: anchored on whichever endpoint HAS bound code, not
    only `flow.src` -- the repo's one real network flow,
    `f_registry_fetch : registry -> vet`, has a foreign/codeless `src`
    but a genuinely provable `dst` (`vet`'s caller code), so checking
    `src` alone made the rule this whole family exists to enforce
    permanently uncheckable-silent on its own motivating case). A flow
    with NEITHER endpoint bound to any code at all is UNCHECKABLE --
    honestly silent rather than a guessed-at proof, the same ceiling
    `_contention.py`'s SYS203 `store_ids` and `_selfconform.py`'s
    `managed` exemption already establish for "the fact this rule needs
    is not always reconstructible" cases. When only one endpoint has
    bound code, that endpoint alone is checked; when both do, either
    endpoint's code evidencing a `timeout=` token is sufficient proof
    (an OR, not an AND -- the obligation is that SOME real call site
    along the flow demonstrably bounds the wait, not that every bound
    file does).

GRAMMAR-DATA CEILING, HONESTLY: `timeout` is a bare Flow attr (no numeric
magnitude) -- `strata-core/src/parse.rs`'s generic `attr KEY=VALUE` clause
only lexes an identifier VALUE (letters/`_`/digits, but not digit-led),
so a real duration literal like `30s` cannot round-trip through today's
surface grammar without a dedicated parser clause (a `strata-core`
change, out of scope: this ticket's scope is `src/frob/strata/**`/
`docs/strata/**`/`tests/unit/strata/**` only). REL200/REL201 therefore
prove PRESENCE of a caller-declared timeout obligation and its code-level
evidence, not a specific bound duration -- `_crash.py`'s existing
`Flow.timeout: Quantity | None` typed field (magnitude-aware, no-hang
check into a crash contract) is a SEPARATE, narrower mechanism this
module does not duplicate or replace; a future grammar ticket adding a
real `timeout <quantity>` flow clause could unify the two, not this one.
"""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: this file's \
# 'only' hits are source-level design-rationale/scope-cut prose (docstrings \
# describing already-implemented internal behavior, verifiable by reading \
# the code they annotate) rather than a separate cross-module contract \
# needing its own tracked invariant, the same disposition _contention.py's \
# own INV006 waiver already uses; disposed as a calibration batch, not \
# claim-by-claim"

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict
from typani.result import Err, Ok, Result

from frob.logging import get_logger

from ._code_binding import bind_code
from ._errors import StrataError
from ._models import KernelModel
from ._waive import apply_waivers

_log = get_logger(__name__)

#: `frob sys audit` rule id for REL200 missing timeout: a flow with no
#: `timeout` attr and no `async`/`local` exemption.
# frob:doc docs/strata/reliability.md#rel2xx-timeout-obligation-t-0640
REL_MISSING_TIMEOUT = "REL200"

#: `frob sys audit` rule id for REL201 unproven timeout: a flow declares
#: `timeout`, but its originating node's bound code has no real
#: `timeout=`-shaped token evidencing it (PROVABILITY CONSTRAINT, T-0331).
# frob:doc docs/strata/reliability.md#rel2xx-timeout-obligation-t-0640
REL_UNPROVEN_TIMEOUT = "REL201"

#: Every REL2xx rule id this module can emit -- the `in_scope` set
#: `_apply_reliability_waivers` hands to `apply_waivers` (module
#: docstring: waiver staleness must be judged only against the rule ids
#: this caller actually owns, `_waive.py`'s `in_scope` discipline).
# frob:doc docs/strata/reliability.md#rel2xx-timeout-obligation-t-0640
RELIABILITY_RULES: frozenset[str] = frozenset(
    {REL_MISSING_TIMEOUT, REL_UNPROVEN_TIMEOUT}
)

#: Flow attr declaring a caller-side timeout obligation discharged
#: (module docstring: presence-only, no magnitude -- the grammar-data
#: ceiling this module ships against).
_TIMEOUT_ATTR = "timeout"

#: Flow attr exempting a fire-and-forget flow from the TIMEOUT
#: obligation -- the SAME bare-marker convention `_crash.py::_ASYNC_ATTR`
#: uses for a queue consumer's no-hang exemption (not imported directly:
#: that constant is `_crash.py`'s own private no-hang-check vocabulary,
#: this module owns its own copy of the identical string for the
#: identical reason, exactly as `_host_isolation.py`/`_krb_movement.py`
#: each keep their own `MULTI_INSTANCE_WAIVER_FAMILIES` copy rather than
#: sharing one mutable set).
_ASYNC_ATTR = "async"

#: Flow attr exempting a flow that does not cross a real process/service
#: boundary at all (e.g. an explicitly-modeled in-process dispatch) --
#: new to this module, the same bare-marker shape as `_ASYNC_ATTR`.
_LOCAL_ATTR = "local"

#: Regex proving a real timeout-shaped keyword argument in bound source
#: text (REL201) -- deliberately narrow (a syntactic token scan, not a
#: semantic call-argument binding): `\btimeout\s*=` matches Python's
#: `requests.get(url, timeout=30)` kwarg shape. Ceiling disclosed in the
#: module docstring: this is NOT a claim that the matched token actually
#: bounds the SAME call the flow models, only that the originating
#: node's bound code contains real evidence of a timeout-shaped
#: construct -- the honest "ship what current tooling supports" line
#: `_contention.py`'s MODE-BLIND framing already established for SYS203.
_TIMEOUT_TOKEN_RE = re.compile(r"\btimeout\s*=")


# frob:doc docs/strata/reliability.md#rel2xx-timeout-obligation-t-0640
class ReliabilityViolation(BaseModel):
    """One REL200/REL201 finding: rule id, the REPORTING node (the flow's
    `src`, the caller who owes the timeout obligation), a human-readable
    detail, and `sub_target` (the flow id -- `_waive.py::
    MULTI_INSTANCE_WAIVER_FAMILIES`'s required `RULE:SUBTARGET` waiver
    discipline, since one node can originate several flows). Mirrors
    `_contention.py::ResourceContentionViolation`'s shape deliberately."""

    model_config = ConfigDict(frozen=True)

    rule: str
    node: str
    detail: str
    sub_target: str


# frob:doc docs/strata/reliability.md#rel2xx-timeout-obligation-t-0640
class ReliabilityReport(BaseModel):
    """Every UNWAIVED REL2xx finding, plus `waived` (T-0174 channel, kept
    for report visibility, never silently dropped). Mirrors
    `_contention.py::ResourceContentionReport`'s shape."""

    model_config = ConfigDict(frozen=True)

    violations: tuple[ReliabilityViolation, ...] = ()
    waived: tuple[ReliabilityViolation, ...] = ()


def _has_timeout_attr(attrs: tuple[str, ...]) -> bool:
    """Whether a flow's `attrs` carries the bare `timeout` marker (module
    docstring: presence-only, no magnitude)."""
    return _TIMEOUT_ATTR in attrs


def _is_exempt(attrs: tuple[str, ...]) -> bool:
    """Whether a flow's `attrs` carries `async` (fire-and-forget) or
    `local` (does not cross a real process/service boundary) -- either
    exempts it from the REL200 TIMEOUT obligation entirely."""
    return _ASYNC_ATTR in attrs or _LOCAL_ATTR in attrs


def _missing_timeout_violations(model: KernelModel) -> list[ReliabilityViolation]:
    """REL200: every flow with no `timeout` attr and no exemption -- every
    `Flow` in this grammar already crosses a real process/service
    boundary by construction (module docstring), so deny-by-default
    applies to the WHOLE flow set, not a filtered subset."""
    violations: list[ReliabilityViolation] = []
    for flow in model.flows:
        if _is_exempt(flow.attrs) or _has_timeout_attr(flow.attrs):
            continue
        _log.warning(
            "reliability: REL200 flow %s (%s -> %s) declares no timeout obligation",
            flow.id,
            flow.src,
            flow.dst,
        )
        violations.append(
            ReliabilityViolation(
                rule=REL_MISSING_TIMEOUT,
                node=flow.src,
                sub_target=flow.id,
                detail=(
                    f"flow {flow.id} ({flow.src} -> {flow.dst}) has no timeout "
                    "obligation (no `timeout` attr, no `async`/`local` exemption)"
                ),
            )
        )
    return violations


def _node_has_bound_code(node_id: str, owner_by_node: dict[str, list[str]]) -> bool:
    """Whether `node_id` owns at least one real source file per `bind_code`
    -- the "can this rule even check?" gate REL201 needs before it can
    honestly claim proof-against-code (module docstring's uncheckable-is-
    silent ceiling)."""
    return bool(owner_by_node.get(node_id))


def _files_evidence_timeout(paths: list[str], root: Path) -> bool:
    """Whether any of `paths` (root-relative) contains a real
    `timeout=`-shaped token (`_TIMEOUT_TOKEN_RE`) -- REL201's proof-
    against-code body. Unreadable files are skipped, never treated as
    proof (fails closed, consistent with every other strata code-binding
    reader's error handling)."""
    for rel in paths:
        try:
            text = (root / rel).read_text(encoding="utf-8")
        except OSError:
            _log.warning("reliability: REL201 could not read bound file %s", rel)
            continue
        if _TIMEOUT_TOKEN_RE.search(text):
            return True
    return False


def _owner_index(owner: dict[str, str]) -> dict[str, list[str]]:
    """`CodeBinding.owner` (file -> node id) inverted to node id -> its
    bound files, in deterministic path order -- the per-node lookup
    `_node_has_bound_code`/`_files_evidence_timeout` both need."""
    by_node: dict[str, list[str]] = {}
    for rel, node_id in sorted(owner.items()):
        by_node.setdefault(node_id, []).append(rel)
    return by_node


def _bound_endpoints(
    flow_src: str, flow_dst: str, owner_by_node: dict[str, list[str]]
) -> list[str]:
    """The subset of `flow`'s endpoints (`src`, `dst`, deduped, src-first
    for stable reporting) that own at least one bound file (T-0758:
    proof-anchoring checks whichever endpoint(s) actually have code, not
    only `src` -- `_node_has_bound_code` applied per endpoint)."""
    endpoints = [flow_src] if flow_src == flow_dst else [flow_src, flow_dst]
    return [node for node in endpoints if _node_has_bound_code(node, owner_by_node)]


def _unproven_timeout_violations(
    model: KernelModel, owner_by_node: dict[str, list[str]], root: Path
) -> list[ReliabilityViolation]:
    """REL201: every flow declaring `timeout` where at least one endpoint
    (`src` or `dst`, T-0758) has bound code, but NONE of the bound
    endpoints' code carries a real timeout-shaped token (PROVABILITY
    CONSTRAINT: bare declaration is never sufficient). A flow whose
    NEITHER endpoint has any bound code at all is skipped -- uncheckable,
    not unproven (module docstring). The reporting `node` is the first
    bound endpoint checked (src if it has code, else dst), matching the
    node whose absent proof the violation actually describes."""
    violations: list[ReliabilityViolation] = []
    for flow in model.flows:
        if not _has_timeout_attr(flow.attrs):
            continue
        bound_endpoints = _bound_endpoints(flow.src, flow.dst, owner_by_node)
        if not bound_endpoints:
            continue
        if any(
            _files_evidence_timeout(owner_by_node[node], root)
            for node in bound_endpoints
        ):
            continue
        reporting_node = bound_endpoints[0]
        _log.warning(
            "reliability: REL201 flow %s declares timeout but bound "
            "endpoint(s) %s have no real timeout= token",
            flow.id,
            bound_endpoints,
        )
        violations.append(
            ReliabilityViolation(
                rule=REL_UNPROVEN_TIMEOUT,
                node=reporting_node,
                sub_target=flow.id,
                detail=(
                    f"flow {flow.id} declares timeout, but bound endpoint(s) "
                    f"{bound_endpoints}'s code has no real timeout=-shaped "
                    "token (proof-against-code, T-0331 PROVABILITY CONSTRAINT)"
                ),
            )
        )
    return violations


def _apply_reliability_waivers(
    model: KernelModel, violations: list[ReliabilityViolation]
):  # noqa: ANN201, E501
    """Apply every node's `waive` clause to `violations` (T-0174), exactly
    `_contention.py::_apply_contention_waivers`'s pattern reused for the
    REL2xx family: `sub_target_of` returns `ReliabilityViolation.
    sub_target` (the flow id) since both rules are registered in
    `MULTI_INSTANCE_WAIVER_FAMILIES` and always carry one."""
    return apply_waivers(
        model,
        violations,
        rule_of=lambda v: v.rule,
        target_of=lambda v: v.node,
        sub_target_of=lambda v: v.sub_target,
        in_scope=lambda rule: rule in RELIABILITY_RULES,
    )


# frob:doc docs/strata/reliability.md#rel2xx-timeout-obligation-t-0640
# frob:ticket T-0640
# frob:tests tests/unit/strata/test_reliability.py::TestMissingTimeout.test_flow_without_timeout_fires  # noqa: E501
def check_reliability_timeouts(
    model: KernelModel, root: Path
) -> Result[ReliabilityReport, StrataError]:
    """The REL2xx TIMEOUT-obligation entrypoint (T-0640): REL200 (missing
    timeout) plus REL201 (declared-but-unproven timeout, proof-against-
    code) across every flow in `model`, waivers already applied. `root` is
    the repo root `_code_binding.py::bind_code` binds against -- `Err`
    propagates `bind_code`'s `AmbiguousCodeBinding` unchanged (deny by
    default, the same discipline `check_self_conformance` uses)."""
    bound = bind_code(model, root)
    if bound.is_err:
        return Err(bound.danger_err)
    owner_by_node = _owner_index(bound.danger_ok.owner)

    violations: list[ReliabilityViolation] = []
    violations.extend(_missing_timeout_violations(model))
    violations.extend(_unproven_timeout_violations(model, owner_by_node, root))
    applied = _apply_reliability_waivers(model, violations)
    waived = tuple(wf.finding for wf in applied.waived)
    stale = tuple(
        ReliabilityViolation(
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
        "reliability: %d violation(s), %d waived, %d stale waiver(s)",
        len(applied.kept) + len(stale),
        len(waived),
        len(applied.stale),
    )
    return Ok(ReliabilityReport(violations=tuple(applied.kept) + stale, waived=waived))


__all__ = [
    "RELIABILITY_RULES",
    "REL_MISSING_TIMEOUT",
    "REL_UNPROVEN_TIMEOUT",
    "ReliabilityReport",
    "ReliabilityViolation",
    "check_reliability_timeouts",
]
