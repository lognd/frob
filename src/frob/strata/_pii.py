"""`std.pii`: first-class personal-data modeling and flow proofs (T-0154,
docs/strata/threat.md#pii-declarations-stdpii-t-0154,
docs/strata/surface.md#node-grammar).

INVESTIGATED FIRST (T-0150 round-1 lesson: reuse, never parallel-build):
the compliance layer (`_compliance.py`, COPPA/GDPR/HIPAA) already proves
regulatory obligations over `subject:`/`jurisdiction:`/`basis:` attrs and
the `Pii` label rung of `LABELS` (`_models.py`); the threat catalog
(`_threat.py`) already proves THREAT003/004-style "every fired obligation
is discharged or explicitly assumed with owner+review" over `may`
capabilities; T-0132 already established the STRING-quoted, `code`-style
`node_prop`/`store_prop` grammar shape (`strata-core/src/parse.rs`) for
values that need non-ident characters (`.`).

This module adds exactly one new thing on top of all three: a `carries
PII_TAG+` surface declaration (mirroring `code GLOB+`) naming WHAT personal
data a node/store holds, one attr per tag (`pii=<category>.<field>`, e.g.
`pii=identifier.email`) -- the SAME attr-desugar convention `code`/`skew`/
`fanout` already use (charter law 1: no new kernel primitive). Everything
else is a JOIN:

- PII001 (catalog): a `carries` tag whose category prefix is not one of
  the fixed seven (`PII_CATEGORIES`) is a malformed declaration -- the
  grammar cannot validate this (STRING is opaque to the parser), so it is
  a structural check here, mirroring `_threat.py::check_catalog_
  completeness`'s deny-by-default shape.
- PII002 (boundary-crossing protection): a PII-carrying node's outbound
  flow into a node at a DIFFERENT `TRUST` level (`_models.py::TRUST`) is a
  fired obligation requiring a `pii:PROTECTION:<flow-id>` claim, ASSUMED
  with owner+review -- there is no structural "encryption/pseudonymization/
  consent" detector (nothing in the kernel observes payload encoding), so
  every crossing is deny-by-default until explicitly assumed, the exact
  THREAT003 discharge shape (`_threat.py::check_discharge_completeness`)
  applied to a capability-free precondition.
- PII003 (retention/erasure join): a PII-carrying node with no `retention=`
  bound (`_compliance.py::_retention_limit`) and no revocation-edge flow
  (`_compliance.py::_REVOCATION_ATTR`) is flagged -- REUSING those two
  compliance helpers directly rather than re-implementing the age-collapse/
  revocation-edge checks a second time (module docstring: "join to
  existing compliance obligations rather than duplicating them"). This is
  deliberately narrower than `_compliance.py`'s own GDPR-RETENTION/
  GDPR-ERASURE checks (which additionally require `jurisdiction:eu-
  resident`) -- PII003 is the JURISDICTION-AGNOSTIC baseline "if you carry
  PII at all, declare how it leaves", GDPR-RETENTION/ERASURE are the
  EU-specific tightening layered on top; a model can fail PII003 and pass
  GDPR-RETENTION (no eu-resident tag) or vice versa is not possible since
  GDPR-RETENTION's precondition is a strict superset-if-eu-resident of
  PII003's Pii-or-above test.
- PII004 (undeclared-PII lint): a flow whose src node carries PII but
  whose own `label` sits BELOW `Pii` in `LABELS` is a flow silently
  under-labeling data it is known (by the source node's declaration) to
  contain -- the model's own `carries` fact contradicts the flow's `label`,
  caught the same way `_check_minimization` catches a flow whose own
  attrs contradict its downstream fate.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from typani.result import Ok, Result

from frob.logging import get_logger

from ._compliance import _retention_limit, _revoked_nodes
from ._errors import StrataError
from ._models import LABELS, Flow, KernelModel, Node

_log = get_logger(__name__)

#: Node attr prefix a `carries "<tag>"` surface statement desugars to
#: (mirrors `_code_binding.py::_CODE_PREFIX`'s `code=<glob>` convention).
_PII_PREFIX = "pii="

#: The fixed seven personal-data categories (T-0154 ticket body). A
#: `carries` tag is `<category>.<field>`, e.g. `"identifier.email"`.
# frob:doc docs/strata/threat.md#pii-declarations-stdpii-t-0154
PII_CATEGORIES: frozenset[str] = frozenset(
    {
        "identifier",
        "contact",
        "financial",
        "health",
        "biometric",
        "behavioral",
        "credentials",
    }
)


# frob:doc docs/strata/threat.md#pii-declarations-stdpii-t-0154
# frob:doc docs/guides/extending/pii-categories.md#pii-categories
class PiiViolation(BaseModel):
    """One PII001-004 finding: a rule id, the firing target (node or flow
    id), and a human detail. Mirrors `_compliance.py::ComplianceViolation`'s
    shape so a caller merging every family's report treats PII
    identically."""

    model_config = ConfigDict(frozen=True)

    rule: str  # PII001 catalog | PII002 boundary | PII003 retention | PII004 lint
    target: str | None = None
    detail: str = ""


# frob:doc docs/strata/threat.md#pii-declarations-stdpii-t-0154
class PiiReport(BaseModel):
    """Every PII001-004 violation, in rule-then-target order."""

    model_config = ConfigDict(frozen=True)

    violations: tuple[PiiViolation, ...] = ()


# frob:doc docs/strata/threat.md#pii-declarations-stdpii-t-0154
def node_pii_tags(node: Node) -> tuple[str, ...]:
    """Every `<category>.<field>` tag `node` declares via `carries`
    (i.e. every `pii=<tag>` attr, `_PII_PREFIX` convention). Public: `_pii.py`
    and `_compliance.py` (retention/erasure join) both read this."""
    return tuple(
        attr[len(_PII_PREFIX) :] for attr in node.attrs if attr.startswith(_PII_PREFIX)
    )


# frob:doc docs/strata/threat.md#pii-declarations-stdpii-t-0154
def node_carries_pii(node: Node) -> bool:
    """Whether `node` declares any PII tag at all -- the join predicate
    `_compliance.py`'s retention/erasure checks extend on (module
    docstring, PII003)."""
    return bool(node_pii_tags(node))


def _pii_category(tag: str) -> str | None:
    """The category prefix of a `<category>.<field>` tag, or `None` if the
    tag has no `.`-separated category segment at all."""
    category, sep, _field = tag.partition(".")
    return category if sep else None


# frob:doc docs/strata/threat.md#pii-declarations-stdpii-t-0154
def check_pii_catalog(model: KernelModel) -> tuple[PiiViolation, ...]:
    """PII001: every `carries` tag's category prefix is one of the fixed
    seven (`PII_CATEGORIES`) -- deny-by-default on a malformed or unknown
    category, since the STRING-quoted grammar cannot validate this at
    parse time (module docstring)."""
    violations: list[PiiViolation] = []
    # frob:waive PERF004 reason="one sort for deterministic order, not per-iteration"
    for node in sorted(model.nodes, key=lambda n: n.id):
        for tag in node_pii_tags(node):
            category = _pii_category(tag)
            if category is None or category not in PII_CATEGORIES:
                _log.warning(
                    "pii: PII001 node %s carries malformed/unknown tag %r", node.id, tag
                )
                violations.append(
                    PiiViolation(
                        rule="PII001",
                        target=node.id,
                        detail=f"node {node.id} carries {tag!r}, whose category is "
                        f"not one of {sorted(PII_CATEGORIES)}",
                    )
                )
    return tuple(violations)


def _pii_protection_claim_id(flow_id: str) -> str:
    """The naming convention a PII002-discharging `Claim.id` must follow:
    `pii:PROTECTION:<flow-id>` -- one canonical home, mirroring
    `_threat.py::_discharge_claim_id` (charter: no duplication)."""
    return f"pii:PROTECTION:{flow_id}"


def _pii_claim_override(
    model: KernelModel, claim_id: str
) -> tuple[bool, PiiViolation | None]:
    """Whether an author-written `Claim` discharges the PII002 obligation
    for `claim_id` -- an ASSUMED claim carrying owner+review, the same
    override shape `_compliance.py::_claim_override` establishes (module
    docstring: regulations/PII sensitivity change, so the staleness bound
    matters)."""
    claim = next((c for c in model.claims if c.id == claim_id), None)
    if claim is None:
        return False, None
    if not claim.assumed:
        return False, None
    if claim.owner is None or claim.review is None:
        return True, PiiViolation(
            rule="PII002",
            target=claim_id,
            detail=f"claim {claim_id!r} is assumed with no owner/review date -- "
            "PII protection claims must be owned and staleness-bound",
        )
    return True, None


# frob:doc docs/strata/threat.md#pii-declarations-stdpii-t-0154
def check_pii_boundary_protection(model: KernelModel) -> tuple[PiiViolation, ...]:
    """PII002: a flow touching a PII-carrying node (EITHER end -- data
    moving into a PII store from elsewhere, or out of one) that crosses a
    DIFFERENT `TRUST` level is a fired obligation requiring an assumed
    `pii:PROTECTION:<flow-id>` claim (owner+review) -- deny-by-default,
    since no structural encryption/pseudonymization/consent detector
    exists (module docstring). Checking both ends (not just `src`) matters:
    the common case is a *collection* flow whose `src` is an ordinary
    principal and whose `dst` is the PII-carrying store -- the PII payload
    is what is being collected, not something the source already held."""
    nodes_by_id = {n.id: n for n in model.nodes}
    violations: list[PiiViolation] = []
    # frob:waive PERF004 reason="one sort for deterministic order, not per-iteration"
    for flow in sorted(model.flows, key=lambda f: f.id):
        src = nodes_by_id.get(flow.src)
        dst = nodes_by_id.get(flow.dst)
        if src is None or dst is None:
            continue
        if not (node_carries_pii(src) or node_carries_pii(dst)):
            continue
        if src.trust == dst.trust:
            continue  # no trust-level change: not a boundary crossing
        claim_id = _pii_protection_claim_id(flow.id)
        overridden, malformed = _pii_claim_override(model, claim_id)
        if malformed is not None:
            violations.append(malformed)
        if overridden:
            continue
        violations.append(_pii002_violation(flow, src, dst, claim_id))
    return tuple(violations)


def _pii002_violation(flow: Flow, src: Node, dst: Node, claim_id: str) -> PiiViolation:
    """Build the PII002 `LintViolation`-shaped finding for an unprotected
    pii-carrying boundary crossing, split out of
    `check_pii_boundary_protection` purely to keep its loop body short."""
    _log.warning(
        "pii: PII002 flow %s (%s -> %s) carries pii across trust "
        "boundary %s -> %s with no declared protection",
        flow.id,
        flow.src,
        flow.dst,
        src.trust,
        dst.trust,
    )
    return PiiViolation(
        rule="PII002",
        target=flow.id,
        detail=f"flow {flow.id} carries pii from {src.id} ({src.trust}) "
        f"to {dst.id} ({dst.trust}) with no declared protection -- "
        f"assume {claim_id!r} with owner+review to discharge",
    )


# frob:doc docs/strata/threat.md#pii-declarations-stdpii-t-0154
def check_pii_retention_erasure(model: KernelModel) -> tuple[PiiViolation, ...]:
    """PII003: every PII-carrying node declares EITHER a `retention=`
    bound OR a revocation-edge flow (or both) -- REUSING `_compliance.py`'s
    `_retention_limit`/`_REVOCATION_ATTR` helpers directly rather than
    re-detecting either fact a second time (module docstring: "join to
    existing compliance obligations rather than duplicating them"). Unlike
    `_compliance.py`'s GDPR-RETENTION/GDPR-ERASURE, this fires on
    `carries` alone -- no jurisdiction tag required, since a `carries`
    declaration is itself a stronger, structural signal than clearance
    label."""
    revoked_nodes = _revoked_nodes(model)
    violations: list[PiiViolation] = []
    # frob:waive PERF004 reason="one sort for deterministic order, not per-iteration"
    for node in sorted(model.nodes, key=lambda n: n.id):
        if not node_carries_pii(node):
            continue
        has_retention = _retention_limit(node.attrs) is not None
        has_erasure = node.id in revoked_nodes
        if has_retention or has_erasure:
            continue
        violations.append(_pii003_violation(node))
    return tuple(violations)


def _pii003_violation(node: Node) -> PiiViolation:
    """Build the PII003 finding for a pii-carrying node with no retention
    bound or erasure path, split out of `check_pii_retention_erasure`
    purely to keep its loop body short."""
    _log.warning(
        "pii: PII003 node %s carries pii with no retention bound or "
        "erasure/revocation path",
        node.id,
    )
    return PiiViolation(
        rule="PII003",
        target=node.id,
        detail=f"node {node.id} carries {node_pii_tags(node)} with no "
        "declared retention= bound and no revocation-edge flow",
    )


# T-0364: dropped the private `_revocation_target_nodes` duplicate of
# `_compliance._revoked_nodes` (identical body, dup group) -- this module
# already imports `_REVOCATION_ATTR`/`_retention_limit` from `_compliance`,
# so importing `_revoked_nodes` too is the same-cost, non-duplicated path.


# frob:doc docs/strata/threat.md#pii-declarations-stdpii-t-0154
def check_pii_undeclared_flow(model: KernelModel) -> tuple[PiiViolation, ...]:
    """PII004: a flow sourced from a PII-carrying node whose own `label`
    sits BELOW `Pii` in `LABELS` is under-labeled -- the model's `carries`
    fact contradicts the flow's declared label."""
    nodes_by_id = {n.id: n for n in model.nodes}
    violations: list[PiiViolation] = []
    # frob:waive PERF004 reason="one sort for deterministic order, not per-iteration"
    for flow in sorted(model.flows, key=lambda f: f.id):
        src = nodes_by_id.get(flow.src)
        if src is None or not node_carries_pii(src):
            continue
        leq = LABELS.leq(flow.label, "Pii")
        is_below = leq.is_ok and leq.danger_ok and flow.label != "Pii"
        if not is_below:
            continue
        _log.warning(
            "pii: PII004 flow %s sourced from pii-carrying node %s is "
            "labeled %s, below Pii",
            flow.id,
            src.id,
            flow.label,
        )
        violations.append(
            PiiViolation(
                rule="PII004",
                target=flow.id,
                detail=f"flow {flow.id} sources from {src.id}, which carries "
                f"{node_pii_tags(src)}, but is labeled {flow.label!r} (below Pii)",
            )
        )
    return tuple(violations)


# frob:doc docs/strata/threat.md#pii-declarations-stdpii-t-0154
def evaluate_pii(model: KernelModel) -> Result[PiiReport, StrataError]:
    """The strata-level PII-audit entrypoint: PII001-004 over `model`
    (module docstring). Kept gate-agnostic (no `src/frob/gates` import),
    mirroring `_compliance.py::evaluate_compliance` /
    `_threat.py::evaluate_threats`."""
    all_violations = (
        *check_pii_catalog(model),
        *check_pii_boundary_protection(model),
        *check_pii_retention_erasure(model),
        *check_pii_undeclared_flow(model),
    )
    _log.info(
        "pii: evaluated %d node(s)/%d flow(s) -> %d violation(s)",
        len(model.nodes),
        len(model.flows),
        len(all_violations),
    )
    return Ok(PiiReport(violations=all_violations))


__all__ = [
    "PII_CATEGORIES",
    "PiiReport",
    "PiiViolation",
    "check_pii_boundary_protection",
    "check_pii_catalog",
    "check_pii_retention_erasure",
    "check_pii_undeclared_flow",
    "evaluate_pii",
    "node_carries_pii",
    "node_pii_tags",
]
