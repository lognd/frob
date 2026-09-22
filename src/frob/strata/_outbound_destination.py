"""SYS114/SYS115: outbound-flow-to-foreign-node surface (T-4113, H3-3,
`design/frob.strata`'s F-307 finding catalog, docs/strata/threat.md
#sys11x-outbound-destination-obligation-t-4113).

F-307 H3-3 (quoted verbatim at the bottom of T-4109's body): SYS100/SYS101
(`_host_isolation_shared.py`/`_krb_movement.py`) are FILE-granular -- a
file granted `net.connect` and observed connecting satisfies the gate
regardless of WHERE it connects to. The flow graph can declare `backend ->
media_host` (a foreign node) but nothing checked that the code's ACTUAL
connection target is constrained to that declared node -- an SSRF surface
invisible to any existing rule. Two sub-findings, bundled in one module
since they share a home (the outbound-flow-to-foreign-node surface) and a
code path (both walk the same flow declarations):

  - SYS114 (destination-constraint): a flow `X -> Y` where `Y` is foreign
    requires the granting file's code (`X`'s bound source, `_code_
    binding.py::bind_code`) to contain a host constraint bound to a
    config field (an allowlist token frob's regex-level tooling can see
    in the source text) at a real outbound-call-shaped site -- absent
    that, the finding fires (deny-by-default, charter law 2: undeclared
    is forbidden) unless the flow carries an explicit `SYS114:<flow-id>`
    waiver. A hardcoded literal host at the same call site is exactly the
    negative case this rule exists to catch, but the PROOF this rule
    looks for is the presence of the config-bound token, not the absence
    of a literal -- the same "presence of evidence, not a specific value"
    honesty line `_reliability.py`'s REL201 draws for `timeout=`.
  - SYS115 (missing-rate lint): among a node's own outbound-to-foreign
    flows, one with no `rate` clause while at least one SIBLING flow
    (same `src`) already declares one is an internal inconsistency worth
    flagging on its own -- narrower and cheaper than SYS114 (module
    docstring's own framing: "implement it first as a stepping stone"),
    and independent of it (a flow can pass SYS114 and still fail SYS115,
    or vice versa). A lone outbound-to-foreign flow with no sibling
    declaring a rate is NOT flagged -- there is nothing to contrast
    against, so this stays a narrow lint, not a REL2xx-style deny-by-
    default obligation (that broader "every outbound flow needs SOME
    obligation" shape already belongs to `_reliability.py`'s REL200/
    REL201 TIMEOUT family, not duplicated here).

**Foreign node**: `_models.py::TRUST`'s bottom rung (`Node.trust ==
"foreign"`) -- the SAME spelling `_pii.py::check_pii_boundary_protection`
and `_export.py`'s k8s NetworkPolicy export already read for "outside this
system's trust perimeter" (this repo's own dogfood example: `registry`,
`design/frob.strata`'s "only foreign-trust node" comment). No new trust
vocabulary.

**Outbound**: a flow `X -> Y` where `Y` (the `dst`) is foreign -- the
OPPOSITE direction of this repo's one real foreign-touching flow
(`f_registry_fetch : registry -> vet`, `src` foreign, modeling response
data flowing IN), which is exactly why frob's own tree has no dogfood
case for this rule (module fixture note in its test file) and why this
rule's own population (`dst` foreign) never overlaps that flow's.

Fixture note (module docstring "honestly disclosed", `_reliability.py`
precedent): frob makes no outbound network call to a foreign host as
part of its own operation, so this module's test coverage is entirely a
synthetic `KernelModel` plus a matching stub source file under
`tests/unit/strata/fixtures/outbound_destination/`, never drawn from
frob's own `design/frob.strata` surface.
"""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict
from typani.result import Err, Ok, Result

from frob.logging import get_logger

from ._code_binding import bind_code
from ._errors import StrataError
from ._models import KernelModel
from ._obligation_proof import owner_index
from ._waive import apply_waivers, stale_relwaive_violations

_log = get_logger(__name__)

#: `frob sys audit` rule id for SYS114: an outbound flow to a foreign node
#: whose granting file's code has no proven config-field-bound host
#: constraint at a connection call site.
# frob:doc docs/strata/threat.md#sys11x-outbound-destination-obligation-t-4113
SYS_UNCONSTRAINED_DESTINATION = "SYS114"

#: `frob sys audit` rule id for SYS115: an outbound-to-foreign flow with
#: no declared `rate` while a sibling outbound-to-foreign flow (same
#: `src`) does declare one.
# frob:doc docs/strata/threat.md#sys11x-outbound-destination-obligation-t-4113
SYS_MISSING_OUTBOUND_RATE = "SYS115"

#: The one `Node.trust` level this rule treats as "outside this system's
#: trust perimeter" (`_models.py::TRUST`'s bottom rung -- the same
#: spelling `_pii.py`/`_export.py` already read).
_FOREIGN_TRUST = "foreign"

#: This module's own waiver-family slices, each passed to `apply_waivers`'
#: `in_scope` (mirrors `_reliability.py::_TIMEOUT_RULES`/`_HEALTH_RULES`'
#: narrow-slice discipline: a shared superset here would make one
#: entrypoint misjudge the OTHER's waivers as stale).
_DESTINATION_RULES: frozenset[str] = frozenset({SYS_UNCONSTRAINED_DESTINATION})
_RATE_RULES: frozenset[str] = frozenset({SYS_MISSING_OUTBOUND_RATE})

#: Regex proving a real config-field-bound host constraint at an outbound-
#: call-shaped site in bound source text (SYS114) -- deliberately narrow
#: (a syntactic token scan, not a semantic call-argument binding, the
#: same honesty line `_reliability.py::_TIMEOUT_TOKEN_RE` draws): a
#: `requests`/`httpx`-shaped call (`get`/`post`/`put`/`request`/
#: `connect`) whose first argument is a dotted attribute access
#: (`config.HOST`, `settings.MEDIA_HOST_URL`) rather than a quoted string
#: literal -- the proof this rule looks for is PRESENCE of that config-
#: bound token, not absence of a literal (module docstring).
_CONFIG_BOUND_HOST_RE = re.compile(
    r"\b(?:get|post|put|request|connect)\(\s*[A-Za-z_]\w*\.[A-Za-z_]\w*"
)


# frob:doc docs/strata/threat.md#sys11x-outbound-destination-obligation-t-4113
class OutboundDestinationViolation(BaseModel):
    """One SYS114/SYS115 finding: rule id, the reporting `node` (always
    the flow's `src`, the caller who owes the obligation), `sub_target`
    (the flow id -- both rules are per-flow multi-instance, REL200/REL201's
    `MULTI_INSTANCE_WAIVER_FAMILIES` shape), and a human detail. Mirrors
    `_reliability.py::ReliabilityViolation`'s shape deliberately."""

    model_config = ConfigDict(frozen=True)

    rule: str
    node: str
    sub_target: str
    detail: str = ""


# frob:doc docs/strata/threat.md#sys11x-outbound-destination-obligation-t-4113
class OutboundDestinationReport(BaseModel):
    """Every unwaived SYS114 or SYS115 finding, plus `waived` (T-0174
    channel, kept for report visibility). Mirrors `_reliability.py::
    ReliabilityReport`'s shape -- one report shape shared by both
    entrypoints below, same as `_reliability.py` shares `ReliabilityReport`
    across `check_reliability_timeouts`/`check_reliability_health`."""

    model_config = ConfigDict(frozen=True)

    violations: tuple[OutboundDestinationViolation, ...] = ()
    waived: tuple[OutboundDestinationViolation, ...] = ()


def _is_foreign(trust: str) -> bool:
    """Whether `trust` is this rule's "outside this system's trust
    perimeter" spelling (`_FOREIGN_TRUST`)."""
    return trust == _FOREIGN_TRUST


def _outbound_foreign_flows(model: KernelModel) -> list:
    """Every flow whose `dst` node is foreign-trust, `src`-then-`id` order
    for stable reporting -- the shared population both SYS114 and SYS115
    walk (module docstring: "both walk the same flow declarations")."""
    nodes_by_id = {n.id: n for n in model.nodes}
    flows = []
    for flow in sorted(model.flows, key=lambda f: (f.src, f.id)):
        dst = nodes_by_id.get(flow.dst)
        if dst is not None and _is_foreign(dst.trust):
            flows.append(flow)
    return flows


# frob:waive EXHAUST003 reason="T-1402: EXHAUST001 narrowed to fire for an own \
# ambiguous bare re-raise; this leaked Unknown traces to an unresolved callee instead \
# (the demoted case). T-1062: leaked Unknown traces to \
# _CONFIG_BOUND_HOST_RE.search(text), a compiled-regex search over an already-decoded \
# str produced by the caught read_text() call; a compiled pattern search cannot raise"
def _files_evidence_config_bound_host(paths: list[str], root: Path) -> bool:
    """Whether any of `paths` (root-relative) contains a real config-
    field-bound host constraint (`_CONFIG_BOUND_HOST_RE`) -- SYS114's
    proof-against-code body, mirroring `_reliability.py::
    _files_evidence_timeout` exactly (unreadable files skipped, never
    treated as proof)."""
    for rel in paths:
        try:
            text = (root / rel).read_text(encoding="utf-8")
        except OSError:
            _log.warning(
                "outbound_destination: SYS114 could not read bound file %s", rel
            )
            continue
        if _CONFIG_BOUND_HOST_RE.search(text):
            return True
    return False


def _unconstrained_destination_violations(
    model: KernelModel, owner_by_node: dict[str, list[str]], root: Path
) -> list[OutboundDestinationViolation]:
    """SYS114: every outbound-to-foreign flow whose `src` node's bound
    code has NO real config-field-bound host constraint -- deny-by-
    default (module docstring: absence of the proof fires, regardless of
    whether a hardcoded literal is also present or the node has no bound
    code at all; an unbound node has nothing constraining its connection
    target either)."""
    violations: list[OutboundDestinationViolation] = []
    for flow in _outbound_foreign_flows(model):
        paths = owner_by_node.get(flow.src, [])
        if _files_evidence_config_bound_host(paths, root):
            continue
        _log.warning(
            "outbound_destination: SYS114 flow %s (%s -> %s) has no proven "
            "config-bound host constraint at its connection call site",
            flow.id,
            flow.src,
            flow.dst,
        )
        violations.append(
            OutboundDestinationViolation(
                rule=SYS_UNCONSTRAINED_DESTINATION,
                node=flow.src,
                sub_target=flow.id,
                detail=(
                    f"flow {flow.id} ({flow.src} -> {flow.dst}) reaches a foreign "
                    "node with no config-field-bound host constraint proven at "
                    "the connection call site (proof-against-code, T-0331 "
                    "PROVABILITY CONSTRAINT) -- an unconstrained SSRF surface"
                ),
            )
        )
    return violations


def _missing_outbound_rate_violations(
    model: KernelModel,
) -> list[OutboundDestinationViolation]:
    """SYS115: among each `src` node's own outbound-to-foreign flows, any
    flow with no `rate` while at least one sibling flow (same `src`) DOES
    declare one -- module docstring: narrower than SYS114, a lint over an
    internal inconsistency, never a bare-absence obligation on its own."""
    flows = _outbound_foreign_flows(model)
    by_src: dict[str, list] = {}
    for flow in flows:
        by_src.setdefault(flow.src, []).append(flow)

    violations: list[OutboundDestinationViolation] = []
    for src in sorted(by_src):
        siblings = by_src[src]
        if not any(f.rate is not None for f in siblings):
            continue  # no sibling proves a rate is even expressible here
        for flow in siblings:
            if flow.rate is not None:
                continue
            _log.warning(
                "outbound_destination: SYS115 flow %s (%s -> %s) has no rate "
                "while a sibling outbound-to-foreign flow from %s declares one",
                flow.id,
                flow.src,
                flow.dst,
                src,
            )
            violations.append(
                OutboundDestinationViolation(
                    rule=SYS_MISSING_OUTBOUND_RATE,
                    node=flow.src,
                    sub_target=flow.id,
                    detail=(
                        f"flow {flow.id} ({flow.src} -> {flow.dst}) declares no "
                        f"rate, but a sibling outbound-to-foreign flow from "
                        f"{src} does"
                    ),
                )
            )
    return violations


def _apply_outbound_waivers(
    model: KernelModel,
    violations: list[OutboundDestinationViolation],
    *,
    family: frozenset[str],
):
    """Apply every node's `waive` clause to `violations` (T-0174), the
    same `apply_waivers` call shape `_reliability.py::
    _apply_reliability_waivers` uses -- `family` is the CALLER's own
    narrow rule-id slice (`_DESTINATION_RULES`/`_RATE_RULES`), never the
    module-wide union (that function's own docstring explains the
    reviewer-caught regression a shared superset causes)."""
    return apply_waivers(
        model,
        violations,
        rule_of=lambda v: v.rule,
        target_of=lambda v: v.node,
        sub_target_of=lambda v: v.sub_target,
        in_scope=lambda rule: rule in family,
    )


# frob:doc docs/strata/threat.md#sys11x-outbound-destination-obligation-t-4113
# frob:ticket T-4113
# frob:enforces CHK-GATE-SYS114
def check_outbound_destination(
    model: KernelModel, root: Path
) -> Result[OutboundDestinationReport, StrataError]:
    """The SYS114 entrypoint (T-4113): every outbound-to-foreign-node flow
    whose granting file's bound code has no proven config-bound host
    constraint, waivers already applied. `root` is the repo root
    `_code_binding.py::bind_code` binds against -- `Err` propagates
    `bind_code`'s `AmbiguousCodeBinding` unchanged (deny by default, the
    same discipline `check_reliability_timeouts` uses)."""
    bound = bind_code(model, root)
    if bound.is_err:
        return Err(bound.danger_err)
    owner_by_node = owner_index(bound.danger_ok.owner)

    violations = _unconstrained_destination_violations(model, owner_by_node, root)
    applied = _apply_outbound_waivers(model, violations, family=_DESTINATION_RULES)
    waived = tuple(wf.finding for wf in applied.waived)
    stale = stale_relwaive_violations(applied.stale, OutboundDestinationViolation)
    _log.info(
        "outbound_destination: SYS114 %d violation(s), %d waived, %d stale waiver(s)",
        len(applied.kept) + len(stale),
        len(waived),
        len(applied.stale),
    )
    return Ok(
        OutboundDestinationReport(violations=tuple(applied.kept) + stale, waived=waived)
    )


# frob:doc docs/strata/threat.md#sys11x-outbound-destination-obligation-t-4113
# frob:ticket T-4113
# frob:enforces CHK-GATE-SYS115
def check_outbound_rate(
    model: KernelModel,
) -> Result[OutboundDestinationReport, StrataError]:
    """The SYS115 entrypoint (T-4113, sibling of `check_outbound_
    destination`): every outbound-to-foreign flow with no `rate` while a
    sibling outbound-to-foreign flow from the same `src` declares one,
    waivers already applied. Purely declarative (no `bind_code`/`root`
    needed -- mirrors `_inbound_rate.py::check_inbound_rate`'s
    declarative-only shape, not `check_outbound_destination`'s code-bound
    one), so this can never `Err`."""
    violations = _missing_outbound_rate_violations(model)
    applied = _apply_outbound_waivers(model, violations, family=_RATE_RULES)
    waived = tuple(wf.finding for wf in applied.waived)
    stale = stale_relwaive_violations(applied.stale, OutboundDestinationViolation)
    _log.info(
        "outbound_destination: SYS115 %d violation(s), %d waived, %d stale waiver(s)",
        len(applied.kept) + len(stale),
        len(waived),
        len(applied.stale),
    )
    return Ok(
        OutboundDestinationReport(violations=tuple(applied.kept) + stale, waived=waived)
    )


__all__ = [
    "SYS_MISSING_OUTBOUND_RATE",
    "SYS_UNCONSTRAINED_DESTINATION",
    "OutboundDestinationReport",
    "OutboundDestinationViolation",
    "check_outbound_destination",
    "check_outbound_rate",
]
