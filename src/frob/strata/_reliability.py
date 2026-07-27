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

T-0644 (child of the same T-0331 epic) adds a THIRD, NODE-level pair to
this same family rather than a separate module (dispatch precedent:
"add your REL2xx rule alongside REL200/REL201" -- one home, no
duplicate rule-module shape per obligation):

  - REL210 missing health surface: a long-lived service/daemon node
    (`node.attrs` carries `unit` -- a systemd unit, T-0261's std.host
    surface -- or `service` -- the Windows SCM analog, same module) with
    no `health` attr declared and no exemption. Deny-by-default, same
    shape as REL200.
  - REL211 unproven health surface: a node DOES declare `health`, but its
    bound code (`_code_binding.py::bind_code`) carries no real
    health/liveness/readiness-probe-shaped token -- the same PROVABILITY
    CONSTRAINT discipline REL201 already established, reusing the exact
    same "no bound code -> uncheckable, not unproven" ceiling.

REL210/REL211 are deliberately NOT added to `_waive.py::
MULTI_INSTANCE_WAIVER_FAMILIES`, unlike REL200/REL201: a node has at
most ONE `unit`/`service` marker and at most one possible REL210/REL211
finding each (there is no per-flow multiplicity here -- a node either
lacks a health declaration or its one declared surface is unproven), so
a bare `waive "REL210" reason="...";` names exactly one thing, the same
"single-instance-per-node families keep the bare-rule form" carve-out
`_waive.py`'s own module docstring already documents for LINT/PII/
COMPLIANCE. Registering a single-fire rule there would force a
meaningless `RULE:SUBTARGET` split for no real sub-target.

GRAMMAR-DATA CEILING, HONESTLY (health): unlike `timeout`'s digit-led-
literal ceiling, `health` needs no magnitude -- it is a bare presence
marker exactly like `async`/`local`, so no strata-core grammar change is
needed here at all. REL211's code-side proof is a syntactic token scan
(`_HEALTH_TOKEN_RE`) over the node's bound source for common health/
liveness/readiness endpoint or probe shapes (e.g. a `/health`-style
route, a `livenessProbe`/`readinessProbe` k8s-manifest-style key, or a
`health_check`/`healthz` identifier) -- the same "presence of evidence,
not a specific endpoint value" honesty line REL201 draws for `timeout=`.
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

#: `frob sys audit` rule id for REL210 missing health surface: a long-
#: lived service/daemon node with no `health` attr and no exemption.
# frob:doc docs/strata/reliability.md#rel21x-health-obligation-t-0644
REL_MISSING_HEALTH = "REL210"

#: `frob sys audit` rule id for REL211 unproven health surface: a node
#: declares `health`, but its bound code has no real health/liveness/
#: readiness-probe-shaped token evidencing it (PROVABILITY CONSTRAINT,
#: T-0331).
# frob:doc docs/strata/reliability.md#rel21x-health-obligation-t-0644
REL_UNPROVEN_HEALTH = "REL211"

#: Every REL2xx rule id EITHER entrypoint in this module can emit --
#: used by `_audit.py::_gap_rule_in_scope`'s cross-family exclusion
#: (that predicate legitimately needs the whole family, since it only
#: needs to know "does some OTHER caller already own this rule id",
#: never "is this specific waiver stale against MY findings"). NOT used
#: for `_apply_reliability_waivers`' own `in_scope` -- each entrypoint
#: passes its OWN narrower family there (`_TIMEOUT_RULES`/
#: `_HEALTH_RULES` below); see `_apply_reliability_waivers`'s docstring
#: for the real regression sharing this superset there caused.
# frob:doc docs/strata/reliability.md#rel2xx-timeout-obligation-t-0640
RELIABILITY_RULES: frozenset[str] = frozenset(
    {
        REL_MISSING_TIMEOUT,
        REL_UNPROVEN_TIMEOUT,
        REL_MISSING_HEALTH,
        REL_UNPROVEN_HEALTH,
    }
)

#: `check_reliability_timeouts`' OWN rule family -- the `in_scope` set it
#: hands `_apply_reliability_waivers`, never the full `RELIABILITY_RULES`
#: (module docstring on `_apply_reliability_waivers`: a shared superset
#: made the health entrypoint misjudge timeout waivers stale, and vice
#: versa in principle).
_TIMEOUT_RULES: frozenset[str] = frozenset({REL_MISSING_TIMEOUT, REL_UNPROVEN_TIMEOUT})

#: `check_reliability_health`'s OWN rule family -- see `_TIMEOUT_RULES`.
_HEALTH_RULES: frozenset[str] = frozenset({REL_MISSING_HEALTH, REL_UNPROVEN_HEALTH})

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

#: Node attrs marking a long-lived service/daemon node (T-0261 std.host
#: surface: `_host.py::_UNIT_ATTR` for a systemd unit, `_host.py::
#: _SERVICE_ATTR` for a Windows SCM service) -- the population REL210/
#: REL211 apply to. Local literal copies, not an import from `_host.py`,
#: for the same import-cycle-avoidance reason `_code_binding.py` keeps
#: its own `_MANAGED_ATTR` copy (module docstring precedent).
_UNIT_ATTR = "unit"
_SERVICE_ATTR = "service"
_DAEMON_ATTRS: frozenset[str] = frozenset({_UNIT_ATTR, _SERVICE_ATTR})

#: Node attr declaring a health/liveness/readiness obligation discharged
#: (presence-only bare marker, same shape as `_ASYNC_ATTR`/`_LOCAL_ATTR`
#: -- module docstring's "no grammar ceiling here at all" note).
_HEALTH_ATTR = "health"

#: Regex proving a real health/liveness/readiness-probe-shaped token in
#: bound source text (REL211) -- deliberately narrow (a syntactic token
#: scan, same honesty line `_TIMEOUT_TOKEN_RE` draws): matches a
#: `/health`-style HTTP route, a k8s-manifest-style `livenessProbe`/
#: `readinessProbe` key, or a `health_check`/`healthz` identifier.
_HEALTH_TOKEN_RE = re.compile(
    r"(/health\w*|/live(?:z|ness)?|/ready(?:z|iness)?"
    r"|livenessProbe|readinessProbe|health_check|healthz)",
    re.IGNORECASE,
)


# frob:doc docs/strata/reliability.md#rel2xx-timeout-obligation-t-0640
class ReliabilityViolation(BaseModel):
    """One REL2xx finding: rule id, the REPORTING node (for REL200/REL201
    the flow's `src`, the caller who owes the timeout obligation; for
    REL210/REL211 the daemon node itself), a human-readable detail, and
    `sub_target`. REL200/REL201 always set `sub_target` to the flow id
    (`_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES`'s required
    `RULE:SUBTARGET` waiver discipline, since one node can originate
    several flows). REL210/REL211 leave it `None` -- single-instance-per-
    node (module docstring: at most one health finding per node per
    rule), the same bare-rule waiver carve-out LINT/PII/COMPLIANCE use.
    Mirrors `_contention.py::ResourceContentionViolation`'s shape
    deliberately."""

    model_config = ConfigDict(frozen=True)

    rule: str
    node: str
    detail: str
    sub_target: str | None = None


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


def _is_daemon_node(attrs: tuple[str, ...]) -> bool:
    """Whether a node's `attrs` carries `unit` or `service` (T-0261
    std.host long-lived daemon markers) -- the population REL210/REL211
    apply to."""
    return any(marker in attrs for marker in _DAEMON_ATTRS)


def _has_health_attr(attrs: tuple[str, ...]) -> bool:
    """Whether a node's `attrs` carries the bare `health` marker (module
    docstring: presence-only, no grammar ceiling for this one)."""
    return _HEALTH_ATTR in attrs


def _missing_health_violations(model: KernelModel) -> list[ReliabilityViolation]:
    """REL210: every long-lived service/daemon node (`_is_daemon_node`)
    with no `health` attr declared -- deny-by-default, same shape as
    REL200 but node-scoped rather than flow-scoped."""
    violations: list[ReliabilityViolation] = []
    for node in model.nodes:
        if not _is_daemon_node(node.attrs) or _has_health_attr(node.attrs):
            continue
        _log.warning(
            "reliability: REL210 node %s declares no health/liveness obligation",
            node.id,
        )
        violations.append(
            ReliabilityViolation(
                rule=REL_MISSING_HEALTH,
                node=node.id,
                detail=(
                    f"node {node.id} is a long-lived service/daemon (unit/service) "
                    "with no health/liveness/readiness obligation (no `health` attr)"
                ),
            )
        )
    return violations


def _files_evidence_health(paths: list[str], root: Path) -> bool:
    """Whether any of `paths` (root-relative) contains a real health/
    liveness/readiness-probe-shaped token (`_HEALTH_TOKEN_RE`) -- REL211's
    proof-against-code body, mirroring `_files_evidence_timeout` exactly
    (unreadable files skipped, never treated as proof)."""
    for rel in paths:
        try:
            text = (root / rel).read_text(encoding="utf-8")
        except OSError:
            _log.warning("reliability: REL211 could not read bound file %s", rel)
            continue
        if _HEALTH_TOKEN_RE.search(text):
            return True
    return False


def _unproven_health_violations(
    model: KernelModel, owner_by_node: dict[str, list[str]], root: Path
) -> list[ReliabilityViolation]:
    """REL211: every daemon node declaring `health` whose bound code HAS
    at least one file (`_node_has_bound_code`) but that code carries no
    real health/liveness/readiness-probe-shaped token (PROVABILITY
    CONSTRAINT: bare declaration is never sufficient). A node with NO
    bound code at all is skipped -- uncheckable, not unproven (module
    docstring, same ceiling REL201 draws)."""
    violations: list[ReliabilityViolation] = []
    for node in model.nodes:
        if not _has_health_attr(node.attrs):
            continue
        if not _node_has_bound_code(node.id, owner_by_node):
            continue
        if _files_evidence_health(owner_by_node[node.id], root):
            continue
        _log.warning(
            "reliability: REL211 node %s declares health but its bound code "
            "has no real health/liveness/readiness token",
            node.id,
        )
        violations.append(
            ReliabilityViolation(
                rule=REL_UNPROVEN_HEALTH,
                node=node.id,
                detail=(
                    f"node {node.id} declares health, but its bound code has no "
                    "real health/liveness/readiness-probe-shaped token "
                    "(proof-against-code, T-0331 PROVABILITY CONSTRAINT)"
                ),
            )
        )
    return violations


def _apply_reliability_waivers(
    model: KernelModel,
    violations: list[ReliabilityViolation],
    *,
    family: frozenset[str],
):  # noqa: ANN201, E501
    """Apply every node's `waive` clause to `violations` (T-0174), exactly
    `_contention.py::_apply_contention_waivers`'s pattern reused for the
    REL2xx family: `sub_target_of` returns `ReliabilityViolation.
    sub_target` -- the flow id for REL200/REL201 (registered in
    `MULTI_INSTANCE_WAIVER_FAMILIES`, always carry one), or `None` for
    REL210/REL211 (single-instance-per-node, module docstring).

    `in_scope` is scoped to the CALLER's own `family` (e.g.
    `{REL_MISSING_TIMEOUT, REL_UNPROVEN_TIMEOUT}` for
    `check_reliability_timeouts`, `{REL_MISSING_HEALTH,
    REL_UNPROVEN_HEALTH}` for `check_reliability_health`), NOT the shared
    `RELIABILITY_RULES` superset -- a real reviewer-caught regression:
    `check_reliability_health` only ever produces REL210/REL211
    violations, so a shared `in_scope=RELIABILITY_RULES` made it treat
    every declared REL200/REL201 waiver (which it can never match, since
    it never sees a REL200/REL201 finding) as STALE, reddening `frob sys
    audit`'s reliability leg on a repo with pre-existing, genuinely-
    effective REL200 waivers (e.g. this repo's own `graph_cache__fill`/
    `graph_cache__inval_f_parse`) even though `check_reliability_timeouts`
    correctly matched and applied those SAME waivers in its own pass. The
    `apply_waivers` docstring's own warning about this exact hazard
    (`_waive.py`, "a caller passes an `in_scope` predicate naming exactly
    the rule ids it owns") -- this function previously violated it by
    passing the whole family to both callers instead of each caller's own
    slice."""
    return apply_waivers(
        model,
        violations,
        rule_of=lambda v: v.rule,
        target_of=lambda v: v.node,
        sub_target_of=lambda v: v.sub_target,
        in_scope=lambda rule: rule in family,
    )


# frob:doc docs/strata/reliability.md#rel2xx-timeout-obligation-t-0640
# frob:ticket T-0640
# frob:ticket T-0958
# frob:enforces SDC-5-TIMEOUT
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
    applied = _apply_reliability_waivers(model, violations, family=_TIMEOUT_RULES)
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


# frob:doc docs/strata/reliability.md#rel21x-health-obligation-t-0644
# frob:ticket T-0644
# frob:tests tests/unit/strata/test_reliability.py::TestMissingHealth.test_daemon_without_health_fires  # noqa: E501
def check_reliability_health(
    model: KernelModel, root: Path
) -> Result[ReliabilityReport, StrataError]:
    """The REL21x HEALTH-obligation entrypoint (T-0644, sibling of
    `check_reliability_timeouts`): REL210 (missing health surface) plus
    REL211 (declared-but-unproven health surface, proof-against-code)
    across every long-lived service/daemon node in `model`, waivers
    already applied. `root` is the repo root `_code_binding.py::
    bind_code` binds against -- `Err` propagates `bind_code`'s
    `AmbiguousCodeBinding` unchanged (deny by default, the same
    discipline `check_reliability_timeouts` uses). A separate entrypoint
    from `check_reliability_timeouts` (rather than folded into it) keeps
    each function's name honest about what it actually checks; both share
    this module's `RELIABILITY_RULES`/waiver-application/`_owner_index`
    machinery (charter: no duplication) and both are wired into `frob sys
    audit` by `frob.app.sys_runner`."""
    bound = bind_code(model, root)
    if bound.is_err:
        return Err(bound.danger_err)
    owner_by_node = _owner_index(bound.danger_ok.owner)

    violations: list[ReliabilityViolation] = []
    violations.extend(_missing_health_violations(model))
    violations.extend(_unproven_health_violations(model, owner_by_node, root))
    applied = _apply_reliability_waivers(model, violations, family=_HEALTH_RULES)
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
        "reliability: %d health violation(s), %d waived, %d stale waiver(s)",
        len(applied.kept) + len(stale),
        len(waived),
        len(applied.stale),
    )
    return Ok(ReliabilityReport(violations=tuple(applied.kept) + stale, waived=waived))


__all__ = [
    "RELIABILITY_RULES",
    "REL_MISSING_HEALTH",
    "REL_MISSING_TIMEOUT",
    "REL_UNPROVEN_HEALTH",
    "REL_UNPROVEN_TIMEOUT",
    "ReliabilityReport",
    "ReliabilityViolation",
    "check_reliability_health",
    "check_reliability_timeouts",
]
