"""REL303: an inbound-rate obligation on a write flow from an
unauthenticated route into a PII/behavioral-carrying store (T-4112, H3-2,
`design/frob.strata`'s F-307 finding catalog, docs/strata/reliability.md
#rel3xx-inbound-rate-obligation-t-4112).

F-307 H3-2 (quoted verbatim at the bottom of T-4109's body): a carries-
bearing store fed from an unauthenticated route had a declared retention
bound (`_compliance.py::_retention_limit`, a TIME bound: how long collected
data is kept) but no declared RATE bound (how much an anonymous caller can
write per unit time) -- unbounded write amplification was invisible to
the gate set before this rule existed. The parent epic frames this as
"REL201-style, applied to writes": `_reliability.py`'s REL201 already
proves an OUTBOUND flow declares a timeout; this rule is the same
discipline in the OPPOSITE direction -- an INBOUND flow into a sensitive
store, gated on the ORIGINATING route's auth posture rather than the
store's.

OWN MODULE, NOT `_reliability.py` (T-4112 grounding, per that ticket's own
instruction): `_reliability.py`'s module docstring tells future REL2xx
authors to "add your rule alongside REL200/REL201, one home" for flows
that share ITS direction (a caller's OWN outbound obligation); this rule
reads the opposite way (an obligation on the RECEIVING store, keyed off the
CALLER's trust level), so it gets its own file and its own REL3xx id,
cross-referencing `_reliability.py`'s constant-naming convention
(`REL_<CONDITION>` module-level strings) without editing that file's
REL200/REL201 pair in place.

**Population**: every `Flow` whose `dst` is a "carries-bearing store" --
this reuses `_pii.py::node_carries_pii` directly (the SAME `carries
"<tag>"` / `pii=<category>.<field>` tag `_pii.py`'s module docstring
already establishes as this repo's one home for "does this node hold
personal/behavioral data", per the "reuse that existing tag, do not
invent a new one" ticket instruction) rather than re-detecting a parallel
notion of "sensitive store".

**Auth posture**: "an unauthenticated route" is a flow whose `src` node
sits at the BOTTOM of the `TRUST` lattice (`_models.py::TRUST`,
`"foreign"`) -- the same trust vocabulary `_pii.py::check_pii_boundary_
protection` already reads off `Node.trust`; "foreign" is this kernel's
one existing spelling of "no auth requirement", so this rule introduces
no new auth vocabulary either.

**The rule**: a flow with `src.trust == "foreign"` and a carries-bearing
`dst` whose declared attrs already carry a retention bound
(`_compliance.py::_retention_limit`) but whose OWN `rate` field
(`_models.py::Flow.rate`, a typed `Quantity | None` -- the SAME field
REL201's parent family and `_facts.py`'s demand propagation already read,
not a new grammar clause) is `None` fires REL303. A flow that already
declares `rate` is proof-complete and stays quiet; a flow whose `dst`
carries no retention bound at all is PII003's problem (`_pii.py`), not
this rule's -- REL303 only tightens the case that already cleared
retention but skipped rate, exactly the finding's own framing ("had a
declared retention bound...but no declared RATE bound").

**Direction discipline** (module docstring instruction: "must not
duplicate REL201 or re-fire on an outbound flow"): this rule only ever
inspects `flow.dst` for the carries-bearing test and `flow.src` for the
trust test -- a flow originating FROM a carries-bearing store (the store
exporting data outward) never matches this population, since its `dst`,
not its `src`, would need to carry the tag for REL303's own inbound-write
shape to apply, and its own `src.trust` is the store's own trust, not an
anonymous caller's.

`REL303` is per-flow multi-instance (one node can receive several inbound
flows), so it joins `_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES` and every
waiver must carry a `REL303:<flow-id>` sub-target, mirroring REL200/REL201.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from typani.result import Ok, Result

from frob.logging import get_logger

from ._compliance import _retention_limit
from ._errors import StrataError
from ._models import KernelModel
from ._pii import node_carries_pii
from ._waive import apply_waivers, stale_relwaive_violations

_log = get_logger(__name__)

#: `frob sys audit` rule id for REL303: an unauthenticated (`trust ==
#: "foreign"`) route's write flow into a carries-bearing store that
#: declares a retention bound but no `rate` bound.
# frob:doc docs/strata/reliability.md#rel3xx-inbound-rate-obligation-t-4112
REL_MISSING_INBOUND_RATE = "REL303"

#: The one `Node.trust` level this rule treats as "no auth requirement"
#: (`_models.py::TRUST`'s bottom rung -- the same spelling `_pii.py::
#: check_pii_boundary_protection` already reads for an unprotected caller).
_UNAUTHENTICATED_TRUST = "foreign"

#: This rule's own waiver family slice, passed to `apply_waivers`'
#: `in_scope` (mirrors `_reliability.py::_TIMEOUT_RULES`'s narrow-slice
#: discipline: a shared multi-rule superset here would be meaningless
#: anyway, since this module owns exactly one rule id, but the same
#: explicit-slice shape is kept for consistency with every other REL/PII
#: family module).
_INBOUND_RATE_RULES: frozenset[str] = frozenset({REL_MISSING_INBOUND_RATE})


# frob:doc docs/strata/reliability.md#rel3xx-inbound-rate-obligation-t-4112
# frob:tests tests/unit/strata/test_inbound_rate.py::TestMissingInboundRate.test_unauthenticated_write_with_retention_but_no_rate_fires  # noqa: E501
class InboundRateViolation(BaseModel):
    """One REL303 finding: the reporting `node` (the route, i.e.
    `flow.src` -- the caller whose write path lacks a declared rate
    bound), the flow's id as `sub_target` (`MULTI_INSTANCE_WAIVER_
    FAMILIES` discipline, REL200/REL201's shape), and a human detail."""

    model_config = ConfigDict(frozen=True)

    rule: str
    node: str
    sub_target: str
    detail: str = ""


# frob:doc docs/strata/reliability.md#rel3xx-inbound-rate-obligation-t-4112
# frob:tests tests/unit/strata/test_inbound_rate.py::TestMissingInboundRate.test_unauthenticated_write_with_retention_but_no_rate_fires  # noqa: E501
class InboundRateReport(BaseModel):
    """Every unwaived REL303 finding, plus `waived` (T-0174 channel, kept
    for report visibility). Mirrors `_reliability.py::ReliabilityReport`'s
    shape."""

    model_config = ConfigDict(frozen=True)

    violations: tuple[InboundRateViolation, ...] = ()
    waived: tuple[InboundRateViolation, ...] = ()


def _is_unauthenticated_route(trust: str) -> bool:
    """Whether `trust` is this rule's one "no auth requirement" spelling
    (`_UNAUTHENTICATED_TRUST`)."""
    return trust == _UNAUTHENTICATED_TRUST


def _missing_inbound_rate_violations(
    model: KernelModel,
) -> list[InboundRateViolation]:
    """REL303: every flow from an unauthenticated (`foreign`-trust) node
    into a carries-bearing store (`_pii.py::node_carries_pii`) that
    already declares a retention bound (`_compliance.py::
    _retention_limit`) but has no declared `rate` -- module docstring's
    "had retention, not rate" framing exactly."""
    nodes_by_id = {n.id: n for n in model.nodes}
    violations: list[InboundRateViolation] = []
    # frob:waive PERF004 reason="one sort for deterministic order, not per-iteration"
    for flow in sorted(model.flows, key=lambda f: f.id):
        src = nodes_by_id.get(flow.src)
        dst = nodes_by_id.get(flow.dst)
        if src is None or dst is None:
            continue
        if not _is_unauthenticated_route(src.trust):
            continue
        if not node_carries_pii(dst):
            continue
        if _retention_limit(dst.attrs) is None:
            continue
        if flow.rate is not None:
            continue
        _log.warning(
            "inbound_rate: REL303 flow %s (%s -> %s) has a retention bound "
            "but no declared rate on an unauthenticated write path",
            flow.id,
            flow.src,
            flow.dst,
        )
        violations.append(
            InboundRateViolation(
                rule=REL_MISSING_INBOUND_RATE,
                node=flow.src,
                sub_target=flow.id,
                detail=(
                    f"flow {flow.id} ({flow.src} -> {flow.dst}) writes from an "
                    "unauthenticated route into a carries-bearing store with a "
                    "declared retention bound but no declared rate bound"
                ),
            )
        )
    return violations


def _apply_inbound_rate_waivers(
    model: KernelModel, violations: list[InboundRateViolation]
):
    """Apply every node's `waive` clause to `violations` (T-0174), the
    same `apply_waivers` call shape `_reliability.py::
    _apply_reliability_waivers` uses -- `sub_target_of` returns the flow
    id (REL303 is registered in `MULTI_INSTANCE_WAIVER_FAMILIES`, so every
    waiver must carry one)."""
    return apply_waivers(
        model,
        violations,
        rule_of=lambda v: v.rule,
        target_of=lambda v: v.node,
        sub_target_of=lambda v: v.sub_target,
        in_scope=lambda rule: rule in _INBOUND_RATE_RULES,
    )


# frob:doc docs/strata/reliability.md#rel3xx-inbound-rate-obligation-t-4112
# frob:ticket T-4112
# frob:enforces CHK-GATE-REL303
# frob:tests tests/unit/strata/test_inbound_rate.py::TestMissingInboundRate.test_unauthenticated_write_with_retention_but_no_rate_fires  # noqa: E501
def check_inbound_rate(model: KernelModel) -> Result[InboundRateReport, StrataError]:
    """The REL303 entrypoint (T-4112): every unauthenticated write flow
    into a carries-bearing store with retention but no rate, waivers
    already applied. Unlike `_reliability.py`'s REL200/REL201, this rule
    needs no code-binding proof-against-code pass -- its precondition
    (trust level, `carries`/`retention=` attrs, a `Flow.rate` field) is
    entirely declarative kernel data, so there is no `bind_code`/`root`
    argument here (mirrors `_pii.py::check_pii_retention_erasure`'s
    declarative-only shape, not `_reliability.py`'s code-bound one)."""
    violations = _missing_inbound_rate_violations(model)
    applied = _apply_inbound_rate_waivers(model, violations)
    waived = tuple(wf.finding for wf in applied.waived)
    stale = stale_relwaive_violations(applied.stale, InboundRateViolation)
    _log.info(
        "inbound_rate: %d violation(s), %d waived, %d stale waiver(s)",
        len(applied.kept) + len(stale),
        len(waived),
        len(applied.stale),
    )
    return Ok(InboundRateReport(violations=tuple(applied.kept) + stale, waived=waived))


__all__ = [
    "REL_MISSING_INBOUND_RATE",
    "InboundRateReport",
    "InboundRateViolation",
    "check_inbound_rate",
]
