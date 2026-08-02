"""std.trust elaborator: surface AST -> kernel facts (docs/strata/surface.md).

A vocabulary is a pure function `surface construct -> kernel facts` (charter
law 1, docs/strata/surface.md#elaborator). `std.trust` is the only
vocabulary this module knows: nodes, flows, endorse/declassify boundaries,
and noflow/reach/bound claims. Elaboration never re-validates what the Rust
parser already guarantees (grammar shape, closed keyword vocabulary); it
only adds the checks the parser cannot make because they span multiple
declarations -- duplicate ids and dangling references.
"""

from __future__ import annotations

from collections import Counter

from typani.result import Err, Ok, Result

from frob.logging import get_logger

from ._ast import (
    BoundaryDecl,
    ClaimDecl,
    FlowDecl,
    Module,
    NodeDecl,
    OperationDecl,
    RefineDecl,
    RemoveDecl,
    ScaleDecl,
    ScenarioDecl,
    StoreDecl,
    TrustDecl,
    _DeployDecl,
    _SecretDecl,
)
from ._code_binding import _CODE_PREFIX
from ._errors import StrataError
from ._host import _host_attrs
from ._infra import elaborate_infra
from ._krb import KrbDelegationKind, _krb_attrs, krb_trust_flows
from ._models import (
    LABELS,
    TRUST,
    Boundary,
    BoundaryDirection,
    BoundClaim,
    CanaryStage,
    Capacity,
    Claim,
    ClaimBody,
    DeployContract,
    Flow,
    FlowCondition,
    KernelModel,
    Metric,
    Node,
    NoFlow,
    Outcome,
    Reach,
    RemoveNode,
    Rewrite,
    ScaleRate,
    Scenario,
    SetTrust,
    Waiver,
)
from ._packs import require_analyzable
from ._pii import _PII_PREFIX
from ._secrets import SecretExpansion, SecretSpec, elaborate_secret
from ._waive import _validate_waiver_fields

_log = get_logger(__name__)

#: Node attr marker for `is_abstract` nodes; refinement proper is T-0062.
_ABSTRACT_ATTR = "abstract"

#: Node attr marker for `managed` nodes (T-0172): external, pure-config
#: infrastructure with no scannable code by declaration (docs/strata/
#: surface.md#key-construct-semantics). `_code_binding.py`/`_threat.py`
#: read this back the same way they read `_ABSTRACT_ATTR`.
_MANAGED_ATTR = "managed"

#: Node attr marker for the `errors total` claim (T-0070).
_ERRORS_TOTAL_ATTR = "errors_total"

#: Node attr marker naming an operation's declared saga/tx coordinator (T-0069).
_COORDINATOR_ATTR = "coordinator"

#: The fixed observe-block log-class vocabulary (docs/strata/policy.md#packs, T-0070).
_OBSERVE_LOG_CLASSES = frozenset(
    {"error_paths", "state_transitions", "boundary_crossings", "crash_events"}
)


def _elaborate_deploy(decl: _DeployDecl) -> DeployContract:
    """One `_DeployDecl` -> one `DeployContract` (T-0136); a direct field-for-field
    mapping onto T-0083's landed kernel construct -- `max_error_rate` is always
    `None` since the surface grammar has no abort-predicate syntax yet."""
    return DeployContract(
        stages=tuple(
            CanaryStage(level=s.level, bake=s.bake, max_error_rate=None)
            for s in decl.stages
        ),
        endorsement_chain=decl.endorsed_by,
        rollback_budget=decl.rollback_budget,
    )


def _node_marker_attrs(decl: NodeDecl, attrs: tuple[str, ...]) -> tuple[str, ...]:
    """Append abstract/managed/errors_total/panics/code/carries markers to `attrs`."""
    if decl.is_abstract:
        _log.debug(
            "node %s is abstract; marking attrs with %r", decl.id, _ABSTRACT_ATTR
        )
        attrs = (*attrs, _ABSTRACT_ATTR)
    if decl.is_managed:
        # T-0172: config-only infra (e.g. a Caddyfile-configured edge) --
        # no `code=` glob is expected or required for it.
        _log.debug("node %s is managed; marking attrs with %r", decl.id, _MANAGED_ATTR)
        attrs = (*attrs, _MANAGED_ATTR)
    if decl.errors_total:
        _log.debug("node %s declares errors_total", decl.id)
        attrs = (*attrs, _ERRORS_TOTAL_ATTR)
    if decl.panics_contained_by is not None:
        _log.debug("node %s: panics contained by %s", decl.id, decl.panics_contained_by)
        attrs = (*attrs, f"panics={decl.panics_contained_by}")
    if decl.code:
        # T-0132: `code GLOB+` -> one `code=<glob>` attr per glob, the
        # convention `_code_binding.py::_node_code_globs` already reads.
        _log.debug("node %s declares %d code glob(s)", decl.id, len(decl.code))
        attrs = (*attrs, *(f"{_CODE_PREFIX}{glob}" for glob in decl.code))
    if decl.carries:
        # T-0154: `carries PII_TAG+` -> one `pii=<tag>` attr per tag, the
        # SAME per-atom attr-desugar convention `code` established
        # (`_pii.py::node_pii_tags` reads this back).
        _log.debug("node %s carries %d pii tag(s)", decl.id, len(decl.carries))
        attrs = (*attrs, *(f"{_PII_PREFIX}{tag}" for tag in decl.carries))
    return attrs


def _node_host_krb_attrs(decl: NodeDecl, attrs: tuple[str, ...]) -> tuple[str, ...]:
    """Append std.host/std.krb desugared attrs to `attrs`."""
    host = _host_attrs(
        runs_as=decl.runs_as,
        is_unit=decl.is_unit,
        owns=tuple((o.path, o.mode) for o in decl.owns),
        listens=decl.listens,
        group=decl.group,
        sudoers=decl.sudoers,
        platform=decl.platform,
        service_account=decl.service_account,
        service_account_gmsa=decl.service_account_gmsa,
        is_service=decl.is_service,
        acl=tuple((a.path, a.rule) for a in decl.acl),
        pipes=decl.pipes,
    )
    if host:
        # T-0255: std.host -- runs_as/unit/owns/listens/group/sudoers
        # (group/sudoers added T-0272) desugar to attrs the SAME way as
        # `_infra.py::_elaborate_store` (`_host.py::_host_attrs`, the one
        # shared encoding for both callers). T-0261 adds the Windows
        # analogs (platform/service_account/service/acl/pipes) the same way.
        _log.debug("node %s declares %d std.host attr(s)", decl.id, len(host))
        attrs = (*attrs, *host)
    krb = _krb_attrs(
        realm=decl.krb_realm,
        is_kdc=decl.krb_is_kdc,
        spns=decl.krb_spns,
        delegation=decl.krb_delegation,
        delegation_targets=decl.krb_delegation_targets,
        trusts=tuple((t.target, t.direction, t.transitive) for t in decl.krb_trusts),
    )
    if krb:
        # T-0262: std.krb -- realm/kdc/spn/delegation/trusts desugar to
        # attrs the SAME way std.host's clauses do just above
        # (`_krb.py::_krb_attrs`, the one shared encoding for this
        # vocabulary).
        _log.debug("node %s declares %d std.krb attr(s)", decl.id, len(krb))
        attrs = (*attrs, *krb)
    return attrs


def _node_declared_attrs(decl: NodeDecl) -> tuple[str, ...]:
    """Desugar a `NodeDecl`'s abstract/managed/errors_total/panics/code/carries/
    std.host/std.krb clauses into `Node.attrs`, in declaration order."""
    attrs = _node_marker_attrs(decl, decl.attrs)
    return _node_host_krb_attrs(decl, attrs)


def _elaborate_node(decl: NodeDecl) -> Node:
    """One `NodeDecl` -> one kernel `Node`; abstract/managed/errors_total/panics/code
    -> attrs, may -> Node.may directly (T-0132), deploy -> Node.deploy directly
    (T-0136)."""
    attrs = _node_declared_attrs(decl)
    capacity = None
    if decl.capacity is not None:
        capacity = Capacity(
            service_rate=decl.capacity.rate,
            replicas_min=decl.capacity.replicas_min,
            replicas_max=decl.capacity.replicas_max,
        )
    deploy = None if decl.deploy is None else _elaborate_deploy(decl.deploy)
    waives = tuple(
        Waiver(rule=w.rule, reason=w.reason, ticket=w.ticket) for w in decl.waives
    )
    return Node(
        id=decl.id,
        trust=decl.trust,
        clearance=decl.clearance,
        may=decl.may,
        attrs=attrs,
        capacity=capacity,
        users=decl.users,
        rate=decl.rate,
        residence=decl.residence,
        deploy=deploy,
        waives=waives,
    )


def _elaborate_flow(decl: FlowDecl) -> Flow:
    """One `FlowDecl` -> one kernel `Flow`; a direct field-for-field mapping."""
    return Flow(
        id=decl.id,
        src=decl.src,
        dst=decl.dst,
        label=decl.label,
        rate=decl.rate,
        age=decl.age,
        size=decl.size,
        transport=decl.transport,
        attrs=decl.attrs,
    )


def _elaborate_boundary(decl: BoundaryDecl) -> Boundary:
    """One `BoundaryDecl` -> one `Boundary`; `kind` maps to `BoundaryDirection`."""
    return Boundary(
        id=decl.id,
        flow_id=decl.flow_id,
        direction=BoundaryDirection(decl.kind),
        from_level=decl.from_level,
        to_level=decl.to_level,
        predicate=decl.predicate,
    )


def _elaborate_claim_body(decl: ClaimDecl) -> ClaimBody:
    """The claim `kind` selects which kernel claim body shape to build.

    The parser's `kind` vocabulary is closed to "noflow"/"reach"/"bound"
    (docs/strata/surface.md grammar); anything else cannot reach this
    function post-parse, so there is no defensive fallback branch here.
    The `assert`s below only narrow the type checker's view of the AST's
    per-kind-optional fields, which the parser has already guaranteed are
    populated for the matching `kind` -- they are not runtime validation.
    """
    if decl.kind == "noflow":
        assert decl.src is not None and decl.dst is not None
        return NoFlow(src=decl.src, dst=decl.dst)
    if decl.kind == "reach":
        assert decl.src is not None and decl.dst is not None
        return Reach(src=decl.src, dst=decl.dst)
    assert (
        decl.metric is not None and decl.target is not None and decl.limit is not None
    )
    return BoundClaim(metric=Metric(decl.metric), target=decl.target, limit=decl.limit)


def _elaborate_claim(decl: ClaimDecl) -> Claim:
    """One `ClaimDecl` -> one kernel `Claim`; assumed/owner/review pass through."""
    return Claim(
        id=decl.id,
        body=_elaborate_claim_body(decl),
        assumed=decl.assumed,
        owner=decl.owner,
        review=decl.review,
    )


def _validate_scenario_trust_rewrite(
    scenario: ScenarioDecl,
    rewrite: TrustDecl,
    known_nodes: set[str],
    trust_levels: frozenset[str],
) -> Result[None, StrataError]:
    """A `TrustDecl` rewrite's target/level check; see `_validate_scenario_rewrite`."""
    if rewrite.node_id not in known_nodes:
        _log.error(
            "scenario %s: trust target %r is not declared", scenario.id, rewrite.node_id
        )
        return Err(StrataError.UnknownReference)
    if rewrite.level not in trust_levels:
        # frob:waive PERF004 reason="runs only on the fail-closed err path"
        _log.error(
            "scenario %s: trust level %r is not in the trust lattice %s",
            scenario.id,
            rewrite.level,
            sorted(trust_levels),
        )
        return Err(StrataError.UnknownLevel)
    return Ok(None)


def _validate_scenario_rewrite(
    scenario: ScenarioDecl,
    rewrite: RemoveDecl | ScaleDecl | TrustDecl,
    known_nodes: set[str],
    known_flows: set[str],
    trust_levels: frozenset[str],
) -> Result[None, StrataError]:
    """One scenario rewrite's target/level check; see `_validate_scenarios`."""
    if isinstance(rewrite, RemoveDecl):
        if rewrite.node_id not in known_nodes:
            _log.error(
                "scenario %s: remove target %r is not declared",
                scenario.id,
                rewrite.node_id,
            )
            return Err(StrataError.UnknownReference)
    elif isinstance(rewrite, ScaleDecl):
        if rewrite.flow_id not in known_flows:
            _log.error(
                "scenario %s: scale target %r is not declared",
                scenario.id,
                rewrite.flow_id,
            )
            return Err(StrataError.UnknownReference)
    else:
        assert isinstance(rewrite, TrustDecl)
        return _validate_scenario_trust_rewrite(
            scenario, rewrite, known_nodes, trust_levels
        )
    return Ok(None)


def _validate_scenarios(module: Module) -> Result[None, StrataError]:
    """Every scenario rewrite target must resolve; every trust level must be known.

    Fail-closed (charter law 2): a `remove`/`scale`/`trust` naming an
    undeclared node/flow, or a `trust` reassignment to a level absent from
    the trust lattice, is `UnknownReference`/`UnknownLevel` -- never a
    silent no-op rewrite (docs/strata/kernel.md#scenario, T-0073).
    """
    known_nodes = _known_node_ids(module)
    known_flows = {f.id for f in module.flows}
    trust_levels = TRUST.elements()
    for scenario in module.scenarios:
        for rewrite in scenario.rewrites:
            checked = _validate_scenario_rewrite(
                scenario, rewrite, known_nodes, known_flows, trust_levels
            )
            if checked.is_err:
                return checked
    return Ok(None)


def _elaborate_rewrite(decl: RemoveDecl | ScaleDecl | TrustDecl) -> Rewrite:
    """One AST rewrite decl -> one kernel `Rewrite` (a field-for-field mapping)."""
    if isinstance(decl, RemoveDecl):
        return RemoveNode(node_id=decl.node_id)
    if isinstance(decl, ScaleDecl):
        return ScaleRate(flow_id=decl.flow_id, factor=decl.factor)
    return SetTrust(node_id=decl.node_id, level=decl.level)


def _elaborate_scenario(decl: ScenarioDecl) -> Scenario:
    """One `ScenarioDecl` -> one kernel `Scenario`; nested claims elaborate in place."""
    return Scenario(
        id=decl.id,
        rewrites=tuple(_elaborate_rewrite(r) for r in decl.rewrites),
        claims=tuple(_elaborate_claim(c) for c in decl.claims),
    )


def _elaborate_secrets(
    secrets: tuple[_SecretDecl, ...], known: dict[str, Node]
) -> Result[tuple[SecretExpansion, ...], StrataError]:
    """Every `_SecretDecl` -> a `SecretSpec` handed to the landed `elaborate_secret`
    (T-0082) -- never re-validating issuer/audience/lifetime/revoke logic here
    (charter law 1: a vocabulary is a pure function, defined exactly once in
    `_secrets.py`). Fails closed on the first `_SecretDecl` `elaborate_secret`
    rejects, same first-error-wins posture as every other `elaborate()` step.
    """
    expansions: list[SecretExpansion] = []
    for decl in secrets:
        spec = SecretSpec(
            id=decl.id,
            issued_by=decl.issued_by,
            audience=decl.audience,
            lifetime=decl.lifetime,
            revoke=decl.revoke,
        )
        expanded = elaborate_secret(spec, known)
        if expanded.is_err:
            return Err(expanded.danger_err)
        expansions.append(expanded.danger_ok)
    return Ok(tuple(expansions))


# frob:ticket T-0148
# frob:invariant INV-034
# invariant spec: [INV-034](invariants/INV-034.md)
# frob:tests tests/unit/strata/test_elaborate.py::TestElaborateValidation.test_duplicate_node_id_fails_closed  # noqa: E501
def _validate_no_duplicates(module: Module) -> Result[None, StrataError]:
    """Node ids and flow ids must each be unique within their own kind.

    This is elaboration-level, not parser-level: the grammar has no notion
    of "already declared", so two nodes sharing an id parse cleanly and
    only become a fault once the elaborator tries to build one kernel
    model out of them.
    """
    for kind, ids in (
        ("node", [n.id for n in module.nodes]),
        ("flow", [f.id for f in module.flows]),
        ("secret", [s.id for s in module.secrets]),
    ):
        if len(ids) != len(set(ids)):
            counts = Counter(ids)
            dupes = sorted(i for i, n in counts.items() if n > 1)
            _log.error("duplicate %s id(s) in module %s: %s", kind, module.name, dupes)
            return Err(StrataError.DuplicateId)
    return Ok(None)


def _validate_waivers(module: Module) -> Result[None, StrataError]:
    """Every node's `waive` clauses must carry a non-blank reason, and any
    `MULTI_INSTANCE_WAIVER_FAMILIES` rule (SYS100/SYS101/THREAT002/
    THREAT003, which can each fire more than once per node) must carry a
    `RULE:SUBTARGET` sub-target -- fails closed at elaborate time
    (`_waive.py::_validate_waiver_fields`'s module docstring: a bare rule
    on one of these families would blanket-suppress every current and
    future finding of that rule on the node, the T-0148 bug reopened at
    node scope; an empty reason is a functional bypass with nothing
    written down to justify it). Elaborate-time (not parse-time) because
    the grammar cannot know which rule families are multi-instance --
    that is a Python-side vocabulary fact (T-0174), same layering as
    every other cross-declaration validator in this module.
    """
    for node in module.nodes:
        for waiver in node.waives:
            checked = _validate_waiver_fields(waiver.rule, waiver.reason)
            if checked.is_err:
                _log.error(
                    "node %s: malformed waive clause rule=%r reason=%r",
                    node.id,
                    waiver.rule,
                    waiver.reason,
                )
                return Err(checked.danger_err)
    return Ok(None)


def _validate_references(module: Module) -> Result[None, StrataError]:
    """Boundary flow references and bound-claim targets must resolve.

    `noflow`/`reach` src/dst are left alone here -- they name either a
    node id or a trust level, and only the kernel's `FactBase` knows the
    model's trust lattice well enough to expand a level into its nodes
    (docs/strata/kernel.md#fact-base), so checking them prematurely would
    duplicate that logic and risk disagreeing with it. Bound-claim targets
    may also name a std.infra node (store/cache/queue/cdn/balancer) --
    those ids are known even though `elaborate_infra` has not run yet,
    since the id itself is a parser-guaranteed field on each infra decl
    (docs/strata/surface.md#std-infra), not something only desugaring
    computes.
    """
    known_nodes = _known_node_ids(module)
    known_flows = {f.id for f in module.flows}
    for boundary in module.boundaries:
        if boundary.flow_id not in known_flows:
            _log.error(
                "boundary %s references unknown flow %r", boundary.id, boundary.flow_id
            )
            return Err(StrataError.UnknownReference)
    for claim in module.claims:
        if claim.kind == "bound" and claim.target not in (known_nodes | known_flows):
            _log.error("claim %s references unknown target %r", claim.id, claim.target)
            return Err(StrataError.UnknownReference)
    return Ok(None)


def _known_node_ids(module: Module) -> set[str]:
    """Every declared node-shaped id: std.trust nodes plus every std.infra construct."""
    ids = {n.id for n in module.nodes}
    ids |= {s.id for s in module.stores}
    ids |= {c.id for c in module.caches}
    ids |= {q.id for q in module.queues}
    ids |= {c.id for c in module.cdns}
    ids |= {b.id for b in module.balancers}
    ids |= {s.id for s in module.secrets}
    return ids


def _append_only_ids(module: Module) -> set[str]:
    """Ids of every node/store carrying the `append_only` marker (audit-only rule)."""
    ids = {n.id for n in module.nodes if "append_only" in n.attrs}
    ids |= {s.id for s in module.stores if s.append_only}
    return ids


def _frame_target_base(target: str) -> str:
    """Strip a frame target's `(...)` selector: `Balance(from)` -> `Balance`."""
    idx = target.find("(")
    return target[:idx] if idx != -1 else target


def _validate_boundary_phase_parse(boundary: BoundaryDecl) -> Result[None, StrataError]:
    """`parse` phase frame entries are forbidden; see `_validate_boundary_phases`."""
    phases = boundary.phases
    assert phases is not None
    if phases.parse is not None and phases.parse.frame:
        _log.error(
            "boundary %s: parse phase frame must be empty, got %s",
            boundary.id,
            phases.parse.frame,
        )
        return Err(StrataError.FrameViolation)
    return Ok(None)


def _validate_boundary_phase_effect(
    boundary: BoundaryDecl, known: set[str]
) -> Result[None, StrataError]:
    """`effect` frame targets must be declared; see `_validate_boundary_phases`."""
    phases = boundary.phases
    assert phases is not None
    if phases.effect is not None:
        for target in phases.effect.frame:
            base = _frame_target_base(target)
            if base not in known:
                _log.error(
                    "boundary %s: effect frame target %r is not declared",
                    boundary.id,
                    target,
                )
                return Err(StrataError.UnknownReference)
    return Ok(None)


def _validate_boundary_phase_record(
    boundary: BoundaryDecl, known: set[str]
) -> Result[None, StrataError]:
    """`record` audit target must be declared; see `_validate_boundary_phases`."""
    phases = boundary.phases
    assert phases is not None
    if phases.record is not None and phases.record.audit_to not in known:
        _log.error(
            "boundary %s: record audit target %r is not declared",
            boundary.id,
            phases.record.audit_to,
        )
        return Err(StrataError.UnknownReference)
    return Ok(None)


def _validate_refuse_frame_targets(
    boundary: BoundaryDecl,
    frame: tuple[str, ...],
    known: set[str],
    append_only: set[str],
) -> Result[None, StrataError]:
    """Each `refuse` frame target must be declared and `append_only`."""
    for target in frame:
        base = _frame_target_base(target)
        if base not in known:
            _log.error(
                "boundary %s: refuse frame target %r is not declared",
                boundary.id,
                target,
            )
            return Err(StrataError.UnknownReference)
        if base not in append_only:
            _log.error(
                "boundary %s: refuse frame target %r is not append_only "
                "(refusal frame is audit-only)",
                boundary.id,
                target,
            )
            return Err(StrataError.FrameViolation)
    return Ok(None)


def _validate_boundary_phase_refuse(
    boundary: BoundaryDecl,
    known: set[str],
    append_only: set[str],
    labels: frozenset[str],
) -> Result[None, StrataError]:
    """`refuse` respond label and frame targets; see `_validate_boundary_phases`."""
    phases = boundary.phases
    assert phases is not None
    if phases.refuse is None:
        return Ok(None)
    if phases.refuse.respond not in labels:
        _log.error(
            "boundary %s: refuse respond label %r is not in the labels lattice %s",
            boundary.id,
            phases.refuse.respond,
            sorted(labels),
        )
        return Err(StrataError.UnknownLevel)
    return _validate_refuse_frame_targets(
        boundary, phases.refuse.frame, known, append_only
    )


def _validate_one_boundary_phases(
    boundary: BoundaryDecl,
    known: set[str],
    append_only: set[str],
    labels: frozenset[str],
) -> Result[None, StrataError]:
    """All four phase checks for one boundary, in fail-closed order."""
    for checked in (
        _validate_boundary_phase_parse(boundary),
        _validate_boundary_phase_effect(boundary, known),
        _validate_boundary_phase_record(boundary, known),
        _validate_boundary_phase_refuse(boundary, known, append_only, labels),
    ):
        if checked.is_err:
            return checked
    return Ok(None)


def _validate_boundary_phases(module: Module) -> Result[None, StrataError]:
    """Structural checks for every `boundary ... { phase_block* }` (T-0069, v0).

    Fails closed: a `parse` phase declaring frame entries (admit/parse
    frames must be empty -- effects before endorsement is exactly what the
    six-phase contract exists to kill, docs/strata/boundary.md#the-six-
    phases); an `effect`/`refuse` frame target that is not a declared node;
    a `refuse` frame target that is not `append_only` (the audit-only
    rule); a `record` audit target that is not declared; or a `refuse`
    `respond` label that is not a level in the labels lattice.
    """
    known = _known_node_ids(module)
    append_only = _append_only_ids(module)
    labels = LABELS.elements()
    for boundary in module.boundaries:
        if boundary.phases is None:
            continue
        checked = _validate_one_boundary_phases(boundary, known, append_only, labels)
        if checked.is_err:
            return checked
    return Ok(None)


def _validate_one_operation(
    op: OperationDecl, known: set[str], coordinator_ids: set[str]
) -> Result[None, StrataError]:
    """One `operation` statement's structural checks; see `_validate_operations`."""
    if op.on not in known:
        _log.error("operation %s: on target %r is not declared", op.id, op.on)
        return Err(StrataError.UnknownReference)
    if op.atomic_via not in known:
        _log.error("operation %s: atomic via %r is not declared", op.id, op.atomic_via)
        return Err(StrataError.UnknownReference)
    if not op.modifies_err and op.atomic_via != op.on:
        if op.atomic_via not in coordinator_ids:
            _log.error(
                "operation %s: cross-store refusal -- atomic via %r is "
                "neither the single store %r holding every Ok-frame target "
                "nor a declared coordinator; distributed atomicity by "
                "wishful thinking is a 'not possible' diagnostic, never a "
                "silent acceptance",
                op.id,
                op.atomic_via,
                op.on,
            )
            return Err(StrataError.CrossStoreAtomicity)
    return Ok(None)


def _validate_operations(module: Module) -> Result[None, StrataError]:
    """Structural checks for every `operation` statement (T-0069, v0).

    Fails closed: `on`/`atomic via` naming an undeclared node; and the
    strong-guarantee check -- a `modifies {} on Err` claim whose `atomic
    via` node is neither the operation's own store (`on`, the single store
    presumed to hold every Ok-frame target in v0's declared-structure
    model) nor a node carrying the `coordinator` attr is a
    `CrossStoreAtomicity` refusal, never a silent pass (docs/strata/
    boundary.md#frames-and-failure-atomicity: "Distributed atomicity by
    wishful thinking is a 'not possible' diagnostic, never a silent
    acceptance.").
    """
    known = _known_node_ids(module)
    coordinator_ids = {n.id for n in module.nodes if _COORDINATOR_ATTR in n.attrs}
    for op in module.operations:
        checked = _validate_one_operation(op, known, coordinator_ids)
        if checked.is_err:
            return checked
    return Ok(None)


def _validate_node_observability(
    decl: NodeDecl | StoreDecl, known: set[str]
) -> Result[None, StrataError]:
    """One node/store's panics/observe checks; see `_validate_observability`.

    T-0247: `decl` is `NodeDecl | StoreDecl` since a store now carries the
    same `errors_total`/`panics_contained_by`/`observe` fields as a node
    (docs/strata/surface.md#key-construct-semantics: a store is a node
    too) -- both share this one check, no store-specific duplicate.
    """
    if decl.panics_contained_by is not None and decl.panics_contained_by not in known:
        _log.error(
            "node %s: panics_contained_by %r is not declared",
            decl.id,
            decl.panics_contained_by,
        )
        return Err(StrataError.UnknownReference)
    observe_checked = _validate_observe_field(decl, known)
    if observe_checked.is_err:
        return observe_checked
    if decl.errors_total and decl.observe is None:
        _log.warning("node %s: errors_total without observe", decl.id)
    return Ok(None)


# frob:ticket T-0361
def _validate_observe_field(
    decl: NodeDecl | StoreDecl, known: set[str]
) -> Result[None, StrataError]:
    """The `observe` half of `_validate_node_observability`: every log class
    is in the fixed vocabulary and the `to` target is a known node id;
    split out of that function's body (T-0361)."""
    if decl.observe is None:
        return Ok(None)
    for log_class in decl.observe.log:
        if log_class not in _OBSERVE_LOG_CLASSES:
            _log.error(
                "node %s: observe log class %r is not in the fixed vocabulary %s",
                decl.id,
                log_class,
                sorted(_OBSERVE_LOG_CLASSES),
            )
            return Err(StrataError.UnknownLogClass)
    if decl.observe.to not in known:
        _log.error(
            "node %s: observe target %r is not declared", decl.id, decl.observe.to
        )
        return Err(StrataError.UnknownReference)
    return Ok(None)


def _validate_observability(module: Module) -> Result[None, StrataError]:
    """Structural checks for `panics_contained_by`/`observe` node properties (T-0070).

    Fails closed: an unknown `panics_contained_by` supervisor or `observe
    ... to` target; an `observe` log class outside the fixed vocabulary
    {error_paths, state_transitions, boundary_crossings, crash_events}
    (docs/strata/policy.md#packs). A node declaring `errors_total` with no
    `observe` block is a non-fatal WARNING diagnostic ("errors_total
    without observe"), not a hard error -- the ERR/OBS *gate* wiring into
    `frob check` is phase 4 (T-0070 scope note). T-0247 extends this walk
    to `module.stores` too -- a store is a node too (docs/strata/
    surface.md#key-construct-semantics), so its `errors_total`/
    `panics_contained_by`/`observe` clauses get the same checks.
    """
    known = _known_node_ids(module)
    # T-0247: stores share the same panics/observe checks as nodes -- a
    # store is a node too, so its `errors_total`/`panics_contained_by`/
    # `observe` clauses get the identical fail-closed validation.
    for decl in (*module.nodes, *module.stores):
        checked = _validate_node_observability(decl, known)
        if checked.is_err:
            return checked
    return Ok(None)


# frob:waive EXHAUST003 reason="T-1402: EXHAUST001 narrowed to fire for an own \
# ambiguous bare re-raise; this leaked Unknown traces to an unresolved callee instead \
# (the demoted case). T-1062: leaked Unknown traces to the `[k.value for k in \
# KrbDelegationKind]` list-comprehension inside the log call, a pure enum-attribute \
# walk the resolver cannot statically bound; the one real raise path \
# (KrbDelegationKind construction) is caught above"
def _validate_node_krb_delegation(decl: NodeDecl) -> Result[None, StrataError]:
    """`delegation` kind/target checks; see `_validate_node_krb`."""
    if decl.krb_delegation is not None:
        try:
            KrbDelegationKind(decl.krb_delegation)
        except ValueError:
            _log.error(
                "node %s: delegation kind %r is not in the fixed vocabulary %s",
                decl.id,
                decl.krb_delegation,
                [k.value for k in KrbDelegationKind],
            )
            return Err(StrataError.UnknownLogClass)
    if decl.krb_delegation_targets and decl.krb_delegation != "constrained":
        _log.error(
            "node %s: delegation target(s) declared but delegation kind "
            "is %r, not 'constrained'",
            decl.id,
            decl.krb_delegation,
        )
        return Err(StrataError.UnknownReference)
    return Ok(None)


def _validate_node_krb(decl: NodeDecl, known: set[str]) -> Result[None, StrataError]:
    """One node's std.krb checks; see `_validate_krb`."""
    if decl.krb_spns and decl.runs_as is None:
        _log.error(
            "node %s: declares spn(s) %s but no runs_as service account "
            "to bind them to",
            decl.id,
            decl.krb_spns,
        )
        return Err(StrataError.MalformedKrb)
    delegation_ok = _validate_node_krb_delegation(decl)
    if delegation_ok.is_err:
        return delegation_ok
    for trust in decl.krb_trusts:
        if trust.target not in known:
            _log.error(
                "node %s: trusts target %r is not declared", decl.id, trust.target
            )
            return Err(StrataError.UnknownReference)
    return Ok(None)


def _validate_krb(module: Module) -> Result[None, StrataError]:
    """Structural checks for std.krb node properties (T-0262).

    Fails closed (law 2): a `delegation` kind outside the fixed vocabulary
    {none, constrained, rbcd, unconstrained}; a `target` clause on any
    delegation kind OTHER than `constrained` (a target spn-set is only
    meaningful there -- silently accepting it under `rbcd`/`unconstrained`
    would let a stray clause pass through unexamined); a `trusts` clause
    naming a node id that is not declared, mirroring `panics_contained_by`'s
    dangling-reference check just above; or a `spn` declared with no
    `runs_as` on the SAME node to bind it to (review finding, T-0262
    round 2) -- an SPN is meaningless without the service-account principal
    it names, so this is a dangling reference by a different name, not a
    valid partial declaration.
    """
    known = _known_node_ids(module)
    for decl in module.nodes:
        checked = _validate_node_krb(decl, known)
        if checked.is_err:
            return checked
    return Ok(None)


def _boundary_phase_flows_for(boundary: BoundaryDecl, src: str) -> list[Flow]:
    """This boundary's `effect`/`record` flows, given its underlying flow's dst."""
    flows: list[Flow] = []
    phases = boundary.phases
    assert phases is not None
    if phases.effect is not None:
        for target in phases.effect.frame:
            base = _frame_target_base(target)
            flows.append(
                Flow(
                    id=f"{boundary.id}__effect_{base}",
                    src=src,
                    dst=base,
                    condition=FlowCondition(outcome=Outcome.OK),
                    attrs=("effect",),
                )
            )
    if phases.record is not None:
        flows.append(
            Flow(
                id=f"{boundary.id}__audit",
                src=src,
                dst=phases.record.audit_to,
                label="Internal",
                attrs=("audit",),
            )
        )
    return flows


def _elaborate_boundary_phase_flows(module: Module) -> tuple[Flow, ...]:
    """Build the outcome-conditioned `effect`/`record` flows a phase block implies.

    WHY these two phases only: `effect` frame targets become `Outcome.OK`-
    conditioned flows from the boundary's underlying flow dst to each
    target (docs/strata/kernel.md's one graph extension); `record`
    generates one unconditioned audit flow labeled Internal. `admit`,
    `parse`, `judge`, and `refuse` carry no flow of their own in v0 --
    validation of their structural rules happens in
    `_validate_boundary_phases`, which this function assumes already ran.
    """
    flows: list[Flow] = []
    base_flow_dst = {f.id: f.dst for f in module.flows}
    for boundary in module.boundaries:
        if boundary.phases is None:
            continue
        src = base_flow_dst.get(boundary.flow_id)
        if (
            src is None
        ):  # pragma: no cover -- `_validate_references` already fails closed
            continue
        flows.extend(_boundary_phase_flows_for(boundary, src))
    return tuple(flows)


def _elaborate_operation_flows(module: Module) -> tuple[Flow, ...]:
    """One outcome-conditioned `Flow` per `modifies` frame target (T-0069)."""
    flows: list[Flow] = []
    for op in module.operations:
        for i, target in enumerate(op.modifies_ok):
            flows.append(
                Flow(
                    id=f"{op.id}__ok_{i}",
                    src=op.on,
                    dst=_frame_target_base(target),
                    condition=FlowCondition(outcome=Outcome.OK),
                    attrs=("modifies",),
                )
            )
        for i, target in enumerate(op.modifies_err):
            flows.append(
                Flow(
                    id=f"{op.id}__err_{i}",
                    src=op.on,
                    dst=_frame_target_base(target),
                    condition=FlowCondition(outcome=Outcome.ERR),
                    attrs=("modifies",),
                )
            )
    return tuple(flows)


def _elaborate_observe_flows(module: Module) -> tuple[Flow, ...]:
    """One Internal-labeled `Flow` per node/store's `observe { ... to IDENT }`
    block.

    T-0247: also walks `module.stores` -- a store is a node too (docs/
    strata/surface.md#key-construct-semantics), so a store's `observe`
    clause needs the same synthesized flow a node's gets. This runs before
    `elaborate_infra` expands stores into `Node`s (`_build_base_kernel_
    model`'s call order), so it must read `module.stores` directly rather
    than the not-yet-built store `Node`s.
    """
    return tuple(
        Flow(
            id=f"{decl.id}__obs",
            src=decl.id,
            dst=decl.observe.to,
            label="Internal",
            attrs=("observe",),
        )
        for decl in (*module.nodes, *module.stores)
        if decl.observe is not None
    )


def _rewire_endpoint(value: str, target: str, bind_to: str) -> str:
    """Replace `value` with `bind_to` when it names the refine target."""
    return bind_to if value == target else value


def _rewrite_flow_claim_for_refine(
    claim: Claim, body: NoFlow | Reach, refine: RefineDecl
) -> Claim:
    """Rewrite a `NoFlow`/`Reach` claim's src/dst; see `_rewrite_claim_for_refine`."""
    if body.src != refine.target and body.dst != refine.target:
        return claim
    new_body = type(body)(
        src=_rewire_endpoint(body.src, refine.target, refine.bind_to),
        dst=_rewire_endpoint(body.dst, refine.target, refine.bind_to),
    )
    _log.info(
        "refine %s: rewriting claim %s endpoint(s) %s -> %s to bind_to %s",
        refine.target,
        claim.id,
        body.src,
        body.dst,
        refine.bind_to,
    )
    return claim.model_copy(update={"body": new_body})


def _rewrite_bound_claim_for_refine(
    claim: Claim, body: BoundClaim, refine: RefineDecl
) -> Claim:
    """Rewrite a `BoundClaim`'s target; see `_rewrite_claim_for_refine`."""
    if body.target != refine.target:
        return claim
    _log.info(
        "refine %s: rewriting claim %s target to bind_to %s",
        refine.target,
        claim.id,
        refine.bind_to,
    )
    return claim.model_copy(
        update={"body": body.model_copy(update={"target": refine.bind_to})}
    )


def _rewrite_claim_for_refine(claim: Claim, refine: RefineDecl) -> Claim:
    """Rewrite one claim's endpoints/target from a refine's abstraction id to `bind_to`.

    Flattening a refine block must not leave a claim dangling on an id that
    no longer exists in the model (the abstract node was just removed), so
    every claim naming the target is re-pointed at `bind_to` -- logged at
    INFO since this changes what the claim literally asserts, even though
    its truth is preserved by the faithfulness checks.
    """
    body = claim.body
    if isinstance(body, NoFlow | Reach):
        return _rewrite_flow_claim_for_refine(claim, body, refine)
    if isinstance(body, BoundClaim):
        return _rewrite_bound_claim_for_refine(claim, body, refine)
    return claim


def _check_refine_no_external_surface(
    refine: RefineDecl, inner_flows: list[Flow], inner_ids: set[str]
) -> Result[None, StrataError]:
    """Faithfulness check 1: no inner flow endpoint escapes the refined assembly."""
    for flow in inner_flows:
        if flow.src not in inner_ids or flow.dst not in inner_ids:
            _log.error(
                "refine %r: inner flow %r (%s -> %s) touches an id outside the "
                "refined assembly (new external surface)",
                refine.target,
                flow.id,
                flow.src,
                flow.dst,
            )
            return Err(StrataError.RefinementViolation)
    return Ok(None)


def _check_refine_no_trust_laundering(
    refine: RefineDecl, target: Node, inner_nodes: list[Node]
) -> Result[None, StrataError]:
    """Faithfulness check 2: no inner node sits below the abstraction's trust."""
    for inner in inner_nodes:
        leq = TRUST.leq(target.trust, inner.trust)
        if leq.is_err:
            return Err(leq.danger_err)
        if not leq.danger_ok:
            _log.error(
                "refine %r: inner node %r trust %r is below abstraction trust "
                "%r (trust laundering)",
                refine.target,
                inner.id,
                inner.trust,
                target.trust,
            )
            return Err(StrataError.RefinementViolation)
    return Ok(None)


def _rewire_flows_for_refine(refine: RefineDecl, flows: list[Flow]) -> None:
    """Rewire every flow endpoint naming `refine.target` to `bind_to`, in place."""
    for i, flow in enumerate(flows):
        if flow.src == refine.target or flow.dst == refine.target:
            new_src = _rewire_endpoint(flow.src, refine.target, refine.bind_to)
            new_dst = _rewire_endpoint(flow.dst, refine.target, refine.bind_to)
            _log.info(
                "refine %s: rewiring flow %s %s -> %s to bind_to %s",
                refine.target,
                flow.id,
                flow.src,
                flow.dst,
                refine.bind_to,
            )
            flows[i] = flow.model_copy(update={"src": new_src, "dst": new_dst})


def _refine_target_node(
    refine: RefineDecl, nodes: dict[str, Node]
) -> Result[Node, StrataError]:
    """The refine's abstract target node, or a `RefinementViolation` error."""
    target = nodes.get(refine.target)
    if target is None:
        _log.error("refine target %r is not declared in the module", refine.target)
        return Err(StrataError.RefinementViolation)
    if _ABSTRACT_ATTR not in target.attrs:
        _log.error("refine target %r is not declared abstract", refine.target)
        return Err(StrataError.RefinementViolation)
    return Ok(target)


def _commit_refine(
    refine: RefineDecl,
    inner_nodes: list[Node],
    inner_flows: list[Flow],
    nodes: dict[str, Node],
    flows: list[Flow],
    claims: list[Claim],
) -> None:
    """Splice inner nodes/flows into `nodes`/`flows` and rewire outer flows/claims."""
    del nodes[refine.target]
    for inner in inner_nodes:
        nodes[inner.id] = inner
    flows.extend(inner_flows)

    _rewire_flows_for_refine(refine, flows)

    for i, claim in enumerate(claims):
        claims[i] = _rewrite_claim_for_refine(claim, refine)


def _check_refine_faithfulness(
    refine: RefineDecl,
    target: Node,
    inner_nodes: list[Node],
    inner_flows: list[Flow],
    inner_ids: set[str],
) -> Result[None, StrataError]:
    """Faithfulness checks 1 and 2 (external surface, trust laundering), in order.

    Faithfulness check 3, budget distribution (parent bounds must cover the
    concrete paths), is DEFERRED to phase 2 -- see docs/strata/surface.md
    #v0-semantics. No check is performed here for it.
    """
    surface_ok = _check_refine_no_external_surface(refine, inner_flows, inner_ids)
    if surface_ok.is_err:
        return surface_ok
    return _check_refine_no_trust_laundering(refine, target, inner_nodes)


def _check_refine_bind_to(
    refine: RefineDecl, inner_ids: set[str]
) -> Result[None, StrataError]:
    """`bind_to` must name one of the refine's own inner node ids."""
    if refine.bind_to not in inner_ids:
        _log.error(
            "refine %r: bind_to %r is not one of the inner node ids %s",
            refine.target,
            refine.bind_to,
            sorted(inner_ids),
        )
        return Err(StrataError.RefinementViolation)
    return Ok(None)


def _apply_refine(
    refine: RefineDecl,
    nodes: dict[str, Node],
    flows: list[Flow],
    claims: list[Claim],
) -> Result[None, StrataError]:
    """Flatten one `refine` block into `nodes`/`flows`/`claims` in place.

    WHY: this is the compositional-proof mechanism (docs/strata/surface.md
    #refinement) -- an abstract node is swapped for its concrete internals
    only once two of the three faithfulness checks pass (no new external
    surface, no trust laundering); the third, budget distribution, is
    DEFERRED to phase 2 and intentionally not checked here. Every outer
    flow and claim endpoint naming the abstraction is rewired to `bind_to`
    so the flattened model has no dangling reference to the removed id.
    """
    resolved = _refine_target_node(refine, nodes)
    if resolved.is_err:
        return Err(resolved.danger_err)
    target = resolved.danger_ok

    inner_nodes = [_elaborate_node(n) for n in refine.nodes]
    inner_flows = [_elaborate_flow(f) for f in refine.flows]
    inner_ids = {n.id for n in inner_nodes}

    checked = _check_refine_preconditions(
        refine, target, inner_nodes, inner_flows, inner_ids
    )
    if checked.is_err:
        return checked

    _commit_refine(refine, inner_nodes, inner_flows, nodes, flows, claims)
    return Ok(None)


def _check_refine_preconditions(
    refine: RefineDecl,
    target: Node,
    inner_nodes: list[Node],
    inner_flows: list[Flow],
    inner_ids: set[str],
) -> Result[None, StrataError]:
    """Faithfulness (1, 2) then `bind_to` checks, in the order `_apply_refine` needs."""
    faithful = _check_refine_faithfulness(
        refine, target, inner_nodes, inner_flows, inner_ids
    )
    if faithful.is_err:
        return faithful
    return _check_refine_bind_to(refine, inner_ids)


def _apply_all_refines(
    module: Module,
    nodes: dict[str, Node],
    flows: list[Flow],
    claims: list[Claim],
) -> Result[None, StrataError]:
    """Apply every `refine` block in declaration order, in place; first-error-wins."""
    for refine in module.refines:
        applied = _apply_refine(refine, nodes, flows, claims)
        if applied.is_err:
            return Err(applied.danger_err)
    return Ok(None)


def _log_unrefined_frontier(nodes: dict[str, Node]) -> None:
    """WARNING per still-abstract node with no refine block (planning signal)."""
    for node in nodes.values():
        if _ABSTRACT_ATTR in node.attrs:
            _log.warning(
                "unrefined frontier: node %r is abstract with no refine block", node.id
            )


def _elaborate_refines(
    module: Module, model: KernelModel
) -> Result[KernelModel, StrataError]:
    """Flatten every `refine` block in `module` into `model`.

    WHY: refinement happens after the base model exists so a refine block
    can reference the already-elaborated abstract node and every outer
    flow/claim built from the rest of the module (docs/strata/surface.md
    #refinement). Any abstract node with no matching refine block is left
    untouched -- that is the unrefined frontier, logged at WARNING as the
    planning-frontier signal rather than an error.
    """
    nodes: dict[str, Node] = {n.id: n for n in model.nodes}
    flows: list[Flow] = list(model.flows)
    claims: list[Claim] = list(model.claims)

    applied = _apply_all_refines(module, nodes, flows, claims)
    if applied.is_err:
        return Err(applied.danger_err)

    _log_unrefined_frontier(nodes)

    return Ok(
        model.model_copy(
            update={
                "nodes": tuple(nodes.values()),
                "flows": tuple(flows),
                "claims": tuple(claims),
            }
        )
    )


def _run_elaborate_validators(module: Module) -> Result[None, StrataError]:
    """Run every cross-declaration validator in the fixed order `elaborate` requires.

    First-error-wins: the exact same order as the inline sequence this
    replaces (duplicates, waivers, references, boundary phases, operations,
    observability, krb, scenarios) -- that order is what determines which
    error surfaces first on a module with more than one fault.
    """
    for validator in (
        _validate_no_duplicates,
        _validate_waivers,
        _validate_references,
        _validate_boundary_phases,
        _validate_operations,
        _validate_observability,
        _validate_krb,
        _validate_scenarios,
    ):
        checked = validator(module)
        if checked.is_err:
            return checked
    return Ok(None)


def _build_base_kernel_model(module: Module) -> KernelModel:
    """Elaborate every top-level construct into the pre-infra/secrets/refine model."""
    elaborated_nodes = tuple(_elaborate_node(n) for n in module.nodes)
    extra_flows = (
        *_elaborate_boundary_phase_flows(module),
        *_elaborate_operation_flows(module),
        *_elaborate_observe_flows(module),
        # T-0262: std.krb domain trusts join the reachability lattice as
        # synthesized Flow edges, same "desugar into an existing kernel
        # primitive" convention the three sources above already use
        # (charter law 1) -- see `_krb.py::krb_trust_flows` module
        # docstring for why this happens here and not as a scenario
        # rewrite.
        *krb_trust_flows(elaborated_nodes),
    )
    return KernelModel(
        nodes=elaborated_nodes,
        flows=(*(_elaborate_flow(f) for f in module.flows), *extra_flows),
        boundaries=tuple(_elaborate_boundary(b) for b in module.boundaries),
        claims=tuple(_elaborate_claim(c) for c in module.claims),
        scenarios=tuple(_elaborate_scenario(s) for s in module.scenarios),
    )


def _expand_model_infra(
    module: Module, model: KernelModel
) -> Result[KernelModel, StrataError]:
    """Run `elaborate_infra` and fold its node/flow/boundary expansion into `model`."""
    infra = elaborate_infra(module, model.nodes, model.flows, model.boundaries)
    if infra.is_err:
        return Err(infra.danger_err)
    expansion = infra.danger_ok
    for diagnostic in expansion.diagnostics:
        _log.warning("std.infra diagnostic: %s", diagnostic)
    return Ok(
        model.model_copy(
            update={
                "nodes": expansion.nodes,
                "flows": expansion.flows,
                "boundaries": expansion.boundaries,
            }
        )
    )


def _expand_model_secrets(
    module: Module, model: KernelModel
) -> Result[KernelModel, StrataError]:
    """Elaborate `module.secrets`, folding node/flow/claim expansion into `model`."""
    known_nodes = {n.id: n for n in model.nodes}
    secrets = _elaborate_secrets(module.secrets, known_nodes)
    if secrets.is_err:
        return Err(secrets.danger_err)
    secret_expansions = secrets.danger_ok
    if not secret_expansions:
        return Ok(model)
    _log.info("elaborated %d secret(s) (T-0136)", len(secret_expansions))
    return Ok(
        model.model_copy(
            update={
                "nodes": (
                    *model.nodes,
                    *(e.node for e in secret_expansions),
                ),
                "flows": (
                    *model.flows,
                    *(f for e in secret_expansions for f in e.flows),
                ),
                "claims": (
                    *model.claims,
                    *(c for e in secret_expansions for c in e.claims),
                ),
            }
        )
    )


def _elaborate_expanded_model(
    module: Module, model: KernelModel
) -> Result[KernelModel, StrataError]:
    """Run the infra -> secrets -> refine expansion stages over the base `model`."""
    infra_expanded = _expand_model_infra(module, model)
    if infra_expanded.is_err:
        return Err(infra_expanded.danger_err)
    model = infra_expanded.danger_ok

    secrets_expanded = _expand_model_secrets(module, model)
    if secrets_expanded.is_err:
        return Err(secrets_expanded.danger_err)
    model = secrets_expanded.danger_ok

    return _elaborate_refines(module, model)


def _log_elaborated_module(module: Module, model: KernelModel) -> KernelModel:
    """INFO-log the elaborated module's shape and return `model` unchanged."""
    _log.info(
        "elaborated module %s: %d node(s), %d flow(s), %d boundary(ies), %d claim(s), "
        "%d refine(s)",
        module.name,
        len(model.nodes),
        len(model.flows),
        len(model.boundaries),
        len(model.claims),
        len(module.refines),
    )
    return model


# frob:doc docs/strata/surface.md#elaborator
def elaborate(module: Module) -> Result[KernelModel, StrataError]:
    """Elaborate a parsed `Module` into a `KernelModel` under `std.trust`.

    WHY: this is the only place that knows what a surface `node`, `flow`,
    `boundary`, or `assert`/`assume` means (charter law 1); the prover
    downstream never sees a vocabulary word. Fails closed, logging at
    ERROR, on cross-declaration faults the Rust parser cannot see:
    duplicate node/flow ids, a boundary naming an unknown flow, or a
    bound claim naming an unknown target.
    """
    normalized = require_analyzable(module)
    if normalized.is_err:
        return Err(normalized.danger_err)
    module = normalized.danger_ok

    validated = _run_elaborate_validators(module)
    if validated.is_err:
        return Err(validated.danger_err)

    model = _build_base_kernel_model(module)

    refined = _elaborate_expanded_model(module, model)
    if refined.is_err:
        return Err(refined.danger_err)
    return Ok(_log_elaborated_module(module, refined.danger_ok))
