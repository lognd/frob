"""KRB001-004: Kerberos/AD delegation-abuse and cross-realm movement
proofs over `std.krb` manifests (T-0263, docs/strata/krb.md#movement-
proofs), the KRB sibling of HOST001/HOST002's compromised-service-owner
family (`_host_isolation.py`, T-0256).

T-0262's `_krb.py` explicitly scoped `KrbManifest.delegation`/`.trusts`
as "unexamined by any obligation rule" -- this module is the examiner:

- **KRB001 (unconstrained delegation)** -- any node declaring
  `delegation unconstrained` is a hard finding: a compromise of that
  node lets it impersonate ANY user to ANY service in the realm, the
  worst lateral+vertical vector std.krb can represent. Fires
  unconditionally (deny-by-default, charter law 2) until re-declared
  constrained/rbcd or waived with a written accepted-risk reason.
- **KRB002 (Kerberoasting exposure)** -- every declared `spn` is
  presumed roastable. Exactly like HOST002's pre-T-0272 `sudoers`
  honest gap (`_host_isolation.py` module docstring): `std.krb` has no
  vocabulary distinguishing a gMSA/machine-account principal from a
  human-memorable one (that grammar lives in `strata-core/src/
  parse.rs`, outside this ticket's `src/frob/strata/**` scope, the
  identical scope cut T-0256 hit before T-0272), so an operator must
  either accept the finding or waive it with a written gMSA/machine-
  account attestation -- never a silent pass.
- **KRB003 (constrained-delegation blast radius)** -- for a node with
  `delegation constrained`, DERIVE the transitive closure of its
  `target` SPNs over every other constrained-delegation node's own
  targets (S4U2Proxy chaining) and prove it never reaches a node whose
  trust is strictly higher than the delegating node's own -- a real
  reachability proof over the SPN-ownership graph
  (`_delegation_reach_higher_trust`), not a check of the immediate
  `target` list alone, with a full witness path on failure.
- **KRB004 (cross-realm containment)** -- prove no node in a
  lower-trust realm reaches a higher-trust node's realm PURELY via a
  domain-trust edge (`_krb.py::krb_trust_flows`'s synthesized `Flow`s,
  already present in `model.flows` at elaboration time). Uses
  `_facts.py::build_facts`/`FactBase.reachable` -- the SAME closure
  engine every `NoFlow` claim is proved over -- so a chain of trusts
  the elaborator already materialized is exactly what this rule walks,
  never a second hand-rolled traversal (charter law 5). Only fires when
  the reaching path actually transits a `krb_trust`-tagged flow: an
  escalation reached by some OTHER declared app flow is a different
  finding (HOST001/002's business, or an ordinary `NoFlow` claim's), not
  this rule's undeclared-trust-path claim.

Every rule is multi-instance-per-node (one KRB002 finding per SPN, one
KRB003/KRB004 finding per distinct higher-trust node reached) --
`KRB_MULTI_INSTANCE_WAIVER_FAMILIES` names the same T-0174
`RULE:SUBTARGET` requirement `HOST_MULTI_INSTANCE_WAIVER_FAMILIES`
established, applied through the same `_waive.py::apply_waivers`
channel, each rule scoped to its own family (`_apply_krb_waivers`
mirrors `_host_isolation.py::_apply_host_waivers`'s per-family `in_scope`
split so one rule's waiver can never silently swallow another's finding).

## Compromised-krb-principal scenario

`_scenarios.py::build_compromised_krb_scenario` reuses the T-0073
scenario engine (the SAME `SetTrust`/`AddFlow`/`NoFlow` primitives
`build_compromised_user_scenario` already reuses for HOST001/HOST002,
T-0256) to prove a compromised krb-bound node's blast radius is bounded
by exactly what its OWN delegation grants -- unconstrained delegation
materializes a synthetic edge to every other node (the true worst-case
reach that finding names), constrained delegation materializes edges
only to its resolved `target` SPNs' owning nodes. A `NoFlow` claim per
node outside that reach set is refuted the moment the closure actually
gets there -- not vacuously proved over an unrelated declared-flow
graph, the exact review-round failure T-0256's Done report records.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from typani.result import Err, Ok, Result

from frob.logging import get_logger

from ._errors import StrataError
from ._facts import build_facts
from ._krb import KrbDelegationKind, KrbManifest, krb_manifest_for
from ._models import KernelModel, Rung
from ._threat import OutOfScopeEntry, WeaknessEntry
from ._waive import WaiverApplication, apply_waivers

_log = get_logger(__name__)

#: KRB001-004 are all multi-instance-per-node (module docstring) -- the
#: same blanket-waiver hazard `HOST_MULTI_INSTANCE_WAIVER_FAMILIES`
#: closes for HOST001/HOST002. Kept as its own constant, not appended to
#: `_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES`, for the identical reason
#: `_host_isolation.py` gives: a bare `waive "KRB001"` clause is rejected
#: the same way a bare `waive "SYS100"` is, without widening the frozen
#: module-level set every OTHER rule family's elaborate-time validation
#: consults.
# frob:doc docs/strata/krb.md#movement-proofs
KRB_MULTI_INSTANCE_WAIVER_FAMILIES: frozenset[str] = frozenset(
    {"KRB001", "KRB002", "KRB003", "KRB004"}
)

#: KRB001's single sub-target -- kept named (not bare `""`) so a `waive
#: "KRB001:unconstrained-delegation"` clause reads the same self-
#: describing way every other multi-instance sub-target does.
_SUB_UNCONSTRAINED = "unconstrained-delegation"

#: Domain-trust `Flow` attr `_krb.py::krb_trust_flows` tags every
#: synthesized trust edge with -- KRB004's "did this path use a trust
#: edge, not a declared app flow" test.
_KRB_TRUST_ATTR = "krb_trust"


# frob:doc docs/strata/krb.md#movement-proofs
class KrbMovementViolation(BaseModel):
    """One KRB001-004 finding: the rule id, the sub-target (module
    docstring -- always present, every rule here is multi-instance-per-
    node), the implicated node, an optional peer/reached node, and a
    human detail."""

    model_config = ConfigDict(frozen=True)

    rule: str  # "KRB001" | "KRB002" | "KRB003" | "KRB004"
    sub_target: str
    node: str
    peer: str | None = None
    detail: str = ""


def _rule_of(v: KrbMovementViolation) -> str:
    """`apply_waivers` extractor: the bare rule family."""
    return v.rule


def _sub_target_of(v: KrbMovementViolation) -> str | None:
    """`apply_waivers` extractor: KRB001-004 are always sub-targeted
    (module docstring), so this is never `None` for a real finding."""
    return v.sub_target


def _target_of(v: KrbMovementViolation) -> str | None:
    """`apply_waivers` extractor: a KRB finding waives against the node
    it was found on -- unlike HOST001's cross-user pair attribution,
    every KRB rule here is anchored to exactly one node (module
    docstring), so there is no "which of two nodes owns this waiver"
    ambiguity to resolve."""
    return v.node


def _manifests_by_node(model: KernelModel) -> dict[str, KrbManifest]:
    """Every node with a declared `std.krb` manifest, keyed by node id --
    the one join every rule below builds its working set from (charter:
    no duplication)."""
    manifests: dict[str, KrbManifest] = {}
    for node in model.nodes:
        manifest = krb_manifest_for(node)
        if manifest is not None:
            manifests[node.id] = manifest
    return manifests


# frob:doc docs/strata/krb.md#movement-proofs
# frob:tests tests/unit/strata/test_krb_movement.py::TestKrb001.test_fires kind="unit"
def evaluate_unconstrained_delegation(
    model: KernelModel,
) -> Result[tuple[KrbMovementViolation, ...], StrataError]:
    """KRB001: every node declaring `delegation unconstrained` is a hard
    finding (module docstring) -- fires unconditionally, deny-by-default,
    never derived away by any other declared fact."""
    manifests = _manifests_by_node(model)
    violations = [
        KrbMovementViolation(
            rule="KRB001",
            sub_target=_SUB_UNCONSTRAINED,
            node=node_id,
            detail=f"node {node_id!r} declares unconstrained delegation -- a "
            "compromise of this node can impersonate ANY user to ANY service "
            "in the realm",
        )
        for node_id, manifest in sorted(manifests.items())
        if manifest.delegation == KrbDelegationKind.UNCONSTRAINED
    ]
    _log.info(
        "krb_movement: KRB001 evaluated %d krb node(s) -> %d violation(s)",
        len(manifests),
        len(violations),
    )
    return Ok(tuple(violations))


# frob:doc docs/strata/krb.md#movement-proofs
# frob:tests tests/unit/strata/test_krb_movement.py::TestKrb002.test_fires kind="unit"
def evaluate_roastable_spn(
    model: KernelModel,
) -> Result[tuple[KrbMovementViolation, ...], StrataError]:
    """KRB002: every declared `spn` is presumed roastable (module
    docstring's honest-gap discipline) -- one finding per SPN, since a
    node may declare more than one."""
    manifests = _manifests_by_node(model)
    violations: list[KrbMovementViolation] = []
    for node_id, manifest in sorted(manifests.items()):
        for spn in manifest.spns:
            violations.append(
                KrbMovementViolation(
                    rule="KRB002",
                    sub_target=spn,
                    node=node_id,
                    detail=f"node {node_id!r} binds SPN {spn!r} to a principal "
                    "with no declared gMSA/machine-account credential class -- "
                    "presumed roastable (offline crackable if the account uses "
                    "a human-memorable password)",
                )
            )
    _log.info(
        "krb_movement: KRB002 evaluated %d krb node(s) -> %d violation(s)",
        len(manifests),
        len(violations),
    )
    return Ok(tuple(violations))


def _spn_owner(manifests: dict[str, KrbManifest]) -> dict[str, str]:
    """SPN value -> the FIRST node id declaring it (last-declaration-wins
    would be surprising here; first-seen is deterministic and matches
    `_host_isolation.py::_owns_by_user`'s own "first stable mapping"
    shape closely enough that a caller need not think about ordering)."""
    owner: dict[str, str] = {}
    for node_id, manifest in sorted(manifests.items()):
        for spn in manifest.spns:
            owner.setdefault(spn, node_id)
    return owner


def _delegation_edges(manifests: dict[str, KrbManifest]) -> dict[str, list[str]]:
    """Node id -> the node ids its `constrained` delegation `target`
    SPNs resolve to (module docstring's S4U2Proxy graph) -- unresolved
    targets (naming no declared SPN) and self-edges are dropped, never
    silently kept as a dangling/self-referential hop."""
    spn_owner = _spn_owner(manifests)
    edges: dict[str, list[str]] = {}
    for node_id, manifest in sorted(manifests.items()):
        if manifest.delegation != KrbDelegationKind.CONSTRAINED:
            continue
        for target_spn in manifest.delegation_targets:
            target_node = spn_owner.get(target_spn)
            if target_node is not None and target_node != node_id:
                edges.setdefault(node_id, []).append(target_node)
    return edges


def _delegation_reach_higher_trust(
    model: KernelModel,
    start: str,
    edges: dict[str, list[str]],
    trust_by_node: dict[str, str],
) -> list[list[str]]:
    """BFS from `start` over the constrained-delegation graph `edges`;
    returns one witness path (`[start, ..., reached]`) per DISTINCT node
    reached whose trust is strictly higher than `start`'s -- the real
    S4U2Proxy-chaining proof KRB003 needs (module docstring), refuted
    the moment ANY hop in the chain lands on higher trust, not just the
    immediate `target` list."""
    start_trust = trust_by_node.get(start)
    if start_trust is None:
        return []
    findings: list[list[str]] = []
    visited = {start}
    frontier: list[list[str]] = [[start]]
    while frontier:
        path = frontier.pop(0)
        current = path[-1]
        for nxt in edges.get(current, ()):
            if nxt in visited:
                continue
            visited.add(nxt)
            new_path = [*path, nxt]
            nxt_trust = trust_by_node.get(nxt)
            if nxt_trust is not None:
                higher = model.trust.leq(start_trust, nxt_trust)
                if higher.is_ok and higher.danger_ok and nxt_trust != start_trust:
                    findings.append(new_path)
            frontier.append(new_path)
    return findings


# frob:doc docs/strata/krb.md#movement-proofs
# frob:tests tests/unit/strata/test_krb_movement.py::TestKrb003.test_chains kind="unit"
def evaluate_constrained_delegation_blast_radius(
    model: KernelModel,
) -> Result[tuple[KrbMovementViolation, ...], StrataError]:
    """KRB003: for every node with `delegation constrained`, prove the
    transitive closure of its `target` SPNs (chained through OTHER
    constrained-delegation nodes' own targets, S4U2Proxy-style) never
    reaches a strictly-higher-trust node (module docstring). Each
    reached higher-trust node is its own finding with a full witness
    path -- never collapsed to "reaches something higher", so a
    counterexample trace is always available."""
    manifests = _manifests_by_node(model)
    trust_by_node = {node.id: node.trust for node in model.nodes}
    edges = _delegation_edges(manifests)
    violations: list[KrbMovementViolation] = []
    for node_id in sorted(edges):
        paths = _delegation_reach_higher_trust(model, node_id, edges, trust_by_node)
        for path in paths:
            target = path[-1]
            violations.append(
                KrbMovementViolation(
                    rule="KRB003",
                    sub_target=target,
                    node=node_id,
                    peer=target,
                    detail=f"node {node_id!r}'s constrained delegation "
                    f"transitively reaches higher-trust node {target!r} via "
                    f"{' -> '.join(path)} (S4U2Proxy chaining)",
                )
            )
    _log.info(
        "krb_movement: KRB003 evaluated %d constrained-delegation node(s) -> "
        "%d violation(s)",
        len(edges),
        len(violations),
    )
    return Ok(tuple(violations))


def _is_krb_trust_flow(facts, flow_id: str) -> bool:  # noqa: ANN001
    """Whether `flow_id` is one of `_krb.py::krb_trust_flows`'s
    synthesized domain-trust edges (KRB004's "reached via an undeclared
    trust path, not an ordinary app flow" test)."""
    flow = facts.flows.get(flow_id)
    return flow is not None and _KRB_TRUST_ATTR in flow.attrs


def _path_uses_krb_trust_flow(facts, path: tuple[str, ...]) -> bool:  # noqa: ANN001
    """Whether any hop of a `FactBase.reachable` witness `path`
    (alternating node/flow ids) is a krb-trust-synthesized `Flow`."""
    return any(_is_krb_trust_flow(facts, flow_id) for flow_id in path[1::2])


# frob:doc docs/strata/krb.md#movement-proofs
# frob:tests tests/unit/strata/test_krb_movement.py::TestKrb004.test_fires kind="unit"
def evaluate_cross_realm_containment(
    model: KernelModel,
) -> Result[tuple[KrbMovementViolation, ...], StrataError]:
    """KRB004: for every node declaring a `realm`, prove no OTHER realm's
    node is reachable from it via `_facts.py::FactBase.reachable` (the
    SAME declared-flow closure every `NoFlow` claim uses, including the
    krb-trust `Flow`s `_krb.py::krb_trust_flows` already synthesizes at
    elaboration time) whose trust is strictly higher AND whose reaching
    path actually transits a krb-trust edge (module docstring) --
    reachability that is proved only via an ordinary declared app `Flow`
    is a different obligation's business, not this rule's."""
    facts_result = build_facts(model)
    if facts_result.is_err:
        return Err(facts_result.danger_err)
    facts = facts_result.danger_ok

    manifests = _manifests_by_node(model)
    realm_by_node = {
        node_id: manifest.realm
        for node_id, manifest in manifests.items()
        if manifest.realm is not None
    }
    trust_by_node = {node.id: node.trust for node in model.nodes}

    violations: list[KrbMovementViolation] = []
    for node_id in sorted(realm_by_node):
        violations.extend(
            _cross_realm_violations_for_node(
                model, facts, node_id, realm_by_node, trust_by_node
            )
        )
    _log.info(
        "krb_movement: KRB004 evaluated %d realm node(s) -> %d violation(s)",
        len(realm_by_node),
        len(violations),
    )
    return Ok(tuple(violations))


def _cross_realm_violations_for_node(
    model: KernelModel,
    facts,  # noqa: ANN001
    node_id: str,
    realm_by_node: dict[str, str],
    trust_by_node: dict[str, str],
) -> list[KrbMovementViolation]:
    """Every KRB004 finding rooted at one realm node (see
    `evaluate_cross_realm_containment`)."""
    src_trust = trust_by_node.get(node_id)
    if src_trust is None:
        return []
    reached = facts.reachable(node_id, through_barriers=True)
    violations: list[KrbMovementViolation] = []
    for target_id in sorted(reached):
        if target_id == node_id:
            continue
        target_realm = realm_by_node.get(target_id)
        if target_realm is None or target_realm == realm_by_node[node_id]:
            continue
        if not _path_uses_krb_trust_flow(facts, reached[target_id]):
            continue
        target_trust = trust_by_node.get(target_id)
        if target_trust is None:
            continue
        higher = model.trust.leq(src_trust, target_trust)
        if higher.is_err or not higher.danger_ok or target_trust == src_trust:
            continue
        violations.append(
            KrbMovementViolation(
                rule="KRB004",
                sub_target=target_id,
                node=node_id,
                peer=target_id,
                detail=f"node {node_id!r} (realm {realm_by_node[node_id]!r}, "
                f"trust {src_trust}) reaches higher-trust node {target_id!r} "
                f"(realm {target_realm!r}, trust {target_trust}) via an "
                "undeclared cross-realm domain-trust path",
            )
        )
    return violations


def _apply_krb_waivers(
    model: KernelModel,
    unconstrained: tuple[KrbMovementViolation, ...],
    roastable: tuple[KrbMovementViolation, ...],
    blast_radius: tuple[KrbMovementViolation, ...],
    cross_realm: tuple[KrbMovementViolation, ...],
) -> tuple[
    WaiverApplication[KrbMovementViolation],
    WaiverApplication[KrbMovementViolation],
    WaiverApplication[KrbMovementViolation],
    WaiverApplication[KrbMovementViolation],
]:
    """Run each KRB rule's findings through `apply_waivers`, scoped to
    its OWN rule family only -- mirrors `_host_isolation.py::
    _apply_host_waivers`'s per-family split so a `KRB002:<spn>` waiver
    considered by KRB001's pass would not double-count as a second
    finding across two different `WaiverApplication`s."""

    def scoped(rule: str, violations: tuple[KrbMovementViolation, ...]):
        return apply_waivers(
            model,
            violations,
            rule_of=_rule_of,
            target_of=_target_of,
            sub_target_of=_sub_target_of,
            in_scope=lambda family, rule=rule: family == rule,
        )

    return (
        scoped("KRB001", unconstrained),
        scoped("KRB002", roastable),
        scoped("KRB003", blast_radius),
        scoped("KRB004", cross_realm),
    )


# frob:doc docs/strata/krb.md#movement-proofs
def evaluate_krb_movement_waived(
    model: KernelModel,
) -> Result[
    tuple[
        WaiverApplication[KrbMovementViolation],
        WaiverApplication[KrbMovementViolation],
        WaiverApplication[KrbMovementViolation],
        WaiverApplication[KrbMovementViolation],
    ],
    StrataError,
]:
    """KRB001 + KRB002 + KRB003 + KRB004, each run through the SAME
    `_waive.py::apply_waivers` T-0174 channel `evaluate_host_isolation_
    waived` uses -- returns `(krb001, krb002, krb003, krb004)`
    `WaiverApplication`s in that order. A `waive
    "KRB001:unconstrained-delegation"` / `"KRB002:<spn>"` /
    `"KRB003:<node>"` / `"KRB004:<node>"` clause on the implicated node
    suppresses that finding only, per `RULE:SUBTARGET` discipline
    (module docstring's `KRB_MULTI_INSTANCE_WAIVER_FAMILIES`)."""
    unconstrained = evaluate_unconstrained_delegation(model)
    if unconstrained.is_err:
        return Err(unconstrained.danger_err)
    roastable = evaluate_roastable_spn(model)
    if roastable.is_err:
        return Err(roastable.danger_err)
    blast_radius = evaluate_constrained_delegation_blast_radius(model)
    if blast_radius.is_err:
        return Err(blast_radius.danger_err)
    cross_realm = evaluate_cross_realm_containment(model)
    if cross_realm.is_err:
        return Err(cross_realm.danger_err)

    return Ok(
        _apply_krb_waivers(
            model,
            unconstrained.danger_ok,
            roastable.danger_ok,
            blast_radius.danger_ok,
            cross_realm.danger_ok,
        )
    )


# frob:doc docs/guides/extending/threat-catalog.md#threat-catalog
# The compromised-domain-principal class (T-0254 ticket body): CWE-269
# (improper privilege management -- KRB001/003's escalation-via-
# delegation class), CWE-284 (improper access control -- KRB004's
# cross-realm class), CWE-522 (insufficiently protected credentials --
# KRB002's roastable-SPN class). Kept in its OWN catalog/view, never
# appended to `_threat.py::CWE_CATALOG`/`VIEWS` -- the same separate-view
# precedent `COMPROMISED_OWNER_CATALOG` set for HOST001/HOST002
# (`_host_isolation.py` module docstring).
KRB_MOVEMENT_CATALOG: tuple[WeaknessEntry, ...] = (
    WeaknessEntry(
        id="CWE-269",
        title="Improper Privilege Management",
        cite="https://cwe.mitre.org/data/definitions/269.html",
        family="security",
        capability_kind=None,  # fired by KRB001/KRB003, not a `may` capability join
        mitigation="krb_movement",
        rung=Rung.L4,
    ),
    WeaknessEntry(
        id="CWE-284",
        title="Improper Access Control",
        cite="https://cwe.mitre.org/data/definitions/284.html",
        family="security",
        capability_kind=None,  # fired by KRB004, not a `may` capability join
        mitigation="krb_movement",
        rung=Rung.L4,
    ),
    WeaknessEntry(
        id="CWE-522",
        title="Insufficiently Protected Credentials",
        cite="https://cwe.mitre.org/data/definitions/522.html",
        family="security",
        capability_kind=None,  # fired by KRB002, not a `may` capability join
        mitigation="krb_movement",
        rung=Rung.L4,
    ),
)

#: No `OutOfScopeEntry` rows: the compromised-domain-principal class
#: names exactly three ids, all cataloged above -- an empty tuple is the
#: honest "nothing excluded" answer for THREAT001-shaped completeness
#: checks run against this view (mirrors `COMPROMISED_OWNER_OUT_OF_SCOPE`'s
#: own empty default).
# frob:doc docs/strata/krb.md#compromised-domain-principal-threat-catalog
KRB_MOVEMENT_OUT_OF_SCOPE: tuple[OutOfScopeEntry, ...] = ()

#: Baseline view for the compromised-domain-principal class (module
#: docstring's separate-view precedent) -- a caller checking this class
#: passes `view="krb-movement-baseline"` plus `KRB_MOVEMENT_CATALOG` to
#: `_threat.py::check_catalog_completeness`'s `views` override, exactly
#: `COMPROMISED_OWNER_VIEWS`'s convention.
# frob:doc docs/strata/krb.md#compromised-domain-principal-threat-catalog
KRB_MOVEMENT_VIEWS: dict[str, frozenset[str]] = {
    "krb-movement-baseline": frozenset(entry.id for entry in KRB_MOVEMENT_CATALOG),
}


__all__ = [
    "KRB_MOVEMENT_CATALOG",
    "KRB_MOVEMENT_OUT_OF_SCOPE",
    "KRB_MOVEMENT_VIEWS",
    "KRB_MULTI_INSTANCE_WAIVER_FAMILIES",
    "KrbMovementViolation",
    "evaluate_constrained_delegation_blast_radius",
    "evaluate_cross_realm_containment",
    "evaluate_krb_movement_waived",
    "evaluate_roastable_spn",
    "evaluate_unconstrained_delegation",
]
