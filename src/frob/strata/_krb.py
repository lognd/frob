"""`std.krb`: Kerberos/Active-Directory domain trust modeling for the strata
kernel (T-0262, docs/strata/krb.md).

The auth pillar of the deploy epic (T-0254), built on `std.host` (T-0255):
a node may declare `realm "NAME"` (the Kerberos realm/AD domain it belongs
to), `kdc` (bare marker: this node is the Key Distribution Center for its
realm), `spn "value"` (a service principal name bound to the node's `runs_as`
service account, T-0255), `delegation none|constrained|rbcd|unconstrained`
plus `target "spn"`+ for constrained delegation, and `trusts IDENT [direction
"..."] [transitive]`+ (a domain trust edge to another realm node) --
`strata-core/src/parse.rs`'s `parse_node`. Charter law 1 (a vocabulary is a
pure function surface -> kernel facts): none of this grows `KernelModel`/
`Node` with a new field. Exactly like `host` before it, each clause desugars
to a plain `Node.attrs` string (`_elaborate.py::_elaborate_node`) -- `krb_
attrs` here is the ONE place that encoding is written. `krb_trusts` is the
one exception that also touches `KernelModel.flows`: a domain trust is a
cross-realm RELATIONSHIP, not a single node's fact, so it additionally
desugars to a synthesized `Flow` (via `AddFlow`-shaped construction at
module-elaboration time, not a scenario rewrite) so the EXISTING reach/
noflow closure machinery can answer "can realm A's tickets reach realm B"
without the kernel growing a second, krb-specific graph traversal
(docs/strata/krb.md#domain-trust-lattice).

`krb_manifest_for` is the read-back half: it reads a `Node`'s attrs into one
typed `KrbManifest`. Platform-neutral by design (docs/strata/krb.md#platform
-neutrality): an SPN and a `runs_as` service account compose identically
whether the account is an MIT/Heimdal keytab principal (linux) or a gMSA/
AD service account (T-0261, windows) -- this module never branches on
`HostPlatform`.

MODEL + VOCABULARY ONLY (this ticket's explicit scope cut, docs/strata/
krb.md#scope): delegation-abuse obligations -- e.g. flagging unconstrained
delegation reachable from an untrusted node, or an RBCD chain that crosses a
trust boundary -- are T-0263's job, not this module's. `KrbManifest.delegation`
is deliberately just a typed enum value here, unexamined by any obligation
rule in this file.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from frob.logging import get_logger

from ._models import Flow, Node

_log = get_logger(__name__)

#: `krb_realm=<name>` attr prefix -- same per-atom `key=value` attr
#: convention `_host.py::_RUNS_AS_PREFIX` uses.
_REALM_PREFIX = "krb_realm="

#: `krb_kdc` bare-marker attr -- mirrors `_host.py::_UNIT_ATTR`'s shape.
_KDC_ATTR = "krb_kdc"

#: `krb_spn=<value>` attr prefix, one per declared `spn` entry.
_SPN_PREFIX = "krb_spn="

#: `krb_delegation=<kind>` attr prefix -- at most one per node.
_DELEGATION_PREFIX = "krb_delegation="

#: `krb_delegation_target=<spn>` attr prefix, one per declared `target` entry.
_DELEGATION_TARGET_PREFIX = "krb_delegation_target="

#: `krb_trust=<target>:<direction>:<transitive>` attr prefix, one per
#: declared `trusts` entry.
_TRUST_PREFIX = "krb_trust="

#: `krb_ticket=<kind>` flow-attr prefix a `flow`'s `authenticates_via`
#: clause desugars to (`strata-core/src/parse.rs::parse_flow`). Read back by
#: `flow_authenticates_via` below; documented here (not `_elaborate.py`)
#: since it is std.krb vocabulary, not a generic flow property.
_TICKET_PREFIX = "krb_ticket="

#: Flow id prefix for a domain-trust edge synthesized from a `trusts`
#: clause -- kept distinguishable from user-authored flow ids so a
#: collision is visible rather than silently overwriting one (law 2).
_TRUST_FLOW_ID_PREFIX = "krb-trust:"


# frob:doc docs/strata/krb.md#surface-grammar
class KrbDelegationKind(StrEnum):
    """The closed vocabulary a node's `delegation` clause may declare.

    `NONE` is the safe default (no delegation configured); `UNCONSTRAINED`
    is the classic lateral-movement crown jewel this ticket exists to make
    representable -- whether it is DANGEROUS in a given design is T-0263's
    obligation, not a fact this enum itself carries.
    """

    NONE = "none"
    CONSTRAINED = "constrained"
    RBCD = "rbcd"
    UNCONSTRAINED = "unconstrained"


# frob:doc docs/strata/krb.md#domain-trust-lattice
class KrbTrust(BaseModel):
    """One `trusts IDENT [direction "..."] [transitive]` desugared attr, read
    back as a typed target/direction/transitive triple."""

    model_config = ConfigDict(frozen=True)

    target: str
    # "one-way" | "two-way", free-text beyond that (law 2: the parser
    # accepts either; the elaborator validates).
    direction: str
    transitive: bool


# frob:doc docs/strata/krb.md#krbmanifest
class KrbManifest(BaseModel):
    """The Kerberos-layer facts `std.krb` desugars a node's attrs into (T-0262).

    Platform-neutral (module docstring): no `HostPlatform`-style
    discriminator here, since none of realm/kdc/spn/delegation/trusts
    differ in shape between an MIT/Heimdal keytab node and a gMSA/AD node --
    only the deploy-time MECHANISM (T-0256/T-0261) differs, not the model.
    """

    model_config = ConfigDict(frozen=True)

    realm: str | None = None
    is_kdc: bool = False
    spns: tuple[str, ...] = ()
    delegation: KrbDelegationKind | None = None
    delegation_targets: tuple[str, ...] = ()
    trusts: tuple[KrbTrust, ...] = ()


# frob:tests tests/unit/strata/test_krb.py::TestKrbAttrs.test_desugars kind="unit"
def _krb_attrs(
    *,
    realm: str | None,
    is_kdc: bool,
    spns: tuple[str, ...],
    delegation: str | None,
    delegation_targets: tuple[str, ...],
    trusts: tuple[tuple[str, str, bool], ...],
) -> tuple[str, ...]:
    """Desugar parsed std.krb node clauses into `Node.attrs` strings.

    The ONE encoding `_elaborate.py::_elaborate_node` calls, mirroring
    `_host.py::_host_attrs`'s shared-encoding role (charter law 5: no
    duplication). `trusts` entries are `(target, direction, transitive)`
    triples, matching `KrbTrustDecl`'s field order.
    """
    attrs: list[str] = []
    if realm is not None:
        attrs.append(f"{_REALM_PREFIX}{realm}")
    if is_kdc:
        attrs.append(_KDC_ATTR)
    attrs.extend(f"{_SPN_PREFIX}{spn}" for spn in spns)
    if delegation is not None:
        attrs.append(f"{_DELEGATION_PREFIX}{delegation}")
    attrs.extend(f"{_DELEGATION_TARGET_PREFIX}{t}" for t in delegation_targets)
    attrs.extend(
        f"{_TRUST_PREFIX}{target}:{direction}:{transitive}"
        for target, direction, transitive in trusts
    )
    return tuple(attrs)


# frob:doc docs/strata/krb.md#krbmanifest
# frob:tests tests/unit/strata/test_krb.py::TestKrbManifest.test_reads kind="unit"
def krb_manifest_for(node: Node) -> KrbManifest | None:
    """Read a `Node`'s std.krb attrs back into a typed `KrbManifest`.

    Returns `None` when the node declares no std.krb construct at all --
    mirrors `_host.py::host_manifest_for`'s "no attrs, no manifest" contract
    exactly (distinct from an empty-but-present one).
    """
    realm, is_kdc, spns, delegation, delegation_targets, trusts, declared = (
        _parse_krb_node_attrs(node.attrs)
    )
    if not declared:
        return None
    _log.debug(
        "node %s: krb manifest realm=%r kdc=%s spns=%d delegation=%s trusts=%d",
        node.id,
        realm,
        is_kdc,
        len(spns),
        delegation,
        len(trusts),
    )
    return KrbManifest(
        realm=realm,
        is_kdc=is_kdc,
        spns=tuple(spns),
        delegation=delegation,
        delegation_targets=tuple(delegation_targets),
        trusts=tuple(trusts),
    )


def _parse_krb_node_attrs(
    attrs: tuple[str, ...],
) -> tuple[
    str | None,
    bool,
    list[str],
    KrbDelegationKind | None,
    list[str],
    list[KrbTrust],
    bool,
]:
    """Parse a node's raw attrs into std.krb manifest fields for `krb_manifest_for`."""
    realm: str | None = None
    is_kdc = False
    spns: list[str] = []
    delegation: KrbDelegationKind | None = None
    delegation_targets: list[str] = []
    trusts: list[KrbTrust] = []
    declared = False
    for attr in attrs:
        if attr.startswith(_REALM_PREFIX):
            realm = attr[len(_REALM_PREFIX) :]
            declared = True
        elif attr == _KDC_ATTR:
            is_kdc = True
            declared = True
        elif attr.startswith(_SPN_PREFIX):
            spns.append(attr[len(_SPN_PREFIX) :])
            declared = True
        elif attr.startswith(_DELEGATION_PREFIX):
            delegation = KrbDelegationKind(attr[len(_DELEGATION_PREFIX) :])
            declared = True
        elif attr.startswith(_DELEGATION_TARGET_PREFIX):
            delegation_targets.append(attr[len(_DELEGATION_TARGET_PREFIX) :])
            declared = True
        elif attr.startswith(_TRUST_PREFIX):
            trusts.append(_parse_krb_trust_attr(attr))
            declared = True
    return realm, is_kdc, spns, delegation, delegation_targets, trusts, declared


def _parse_krb_trust_attr(attr: str) -> KrbTrust:
    """Parse one `krb_trust=<target>:<direction>:<transitive>` attr."""
    target, _, rest = attr[len(_TRUST_PREFIX) :].partition(":")
    direction, _, transitive_s = rest.partition(":")
    return KrbTrust(
        target=target, direction=direction, transitive=transitive_s == "True"
    )


# frob:doc docs/strata/krb.md#domain-trust-lattice
# frob:tests tests/unit/strata/test_krb.py::TestKrbTrustFlows.test_sync kind="unit"
def krb_trust_flows(nodes: tuple[Node, ...]) -> tuple[Flow, ...]:
    """Synthesize one `Flow` per declared `trusts` edge (two for `two-way`).

    Elaboration-time only (`_elaborate.py::_elaborate_module` calls this
    after nodes are built), NOT a scenario rewrite -- domain trust is a
    standing fact of the design, not a counterfactual (module docstring).
    Dangling `target` references (a `trusts` clause naming a node id that
    does not exist) are silently skipped here; `_elaborate.py`'s existing
    dangling-reference validation catches every `Flow.src`/`Flow.dst` the
    SAME way it already catches a `flow` statement's own dangling src/dst,
    so this function does not need its own duplicate check (charter law 5).

    T-0282: a trust with `transitive=False` gets the `krb_no_transit` attr
    on its synthesized `Flow`, which `FactBase.reachable` (`_facts.py`)
    reads to mark the edge non-transitive at the kernel boundary
    (`strata-core/src/lib.rs::reachable`'s terminal-edge support) -- the
    edge's `dst` is reachable directly but the BFS does not chain past it,
    so a chain of non-transitive one-way trusts no longer over-reaches the
    way a chain of transitive ones correctly does (docs/strata/krb.md
    #domain-trust-lattice).
    """
    known_ids = {n.id for n in nodes}
    flows: list[Flow] = []
    for node in nodes:
        flows.extend(_krb_trust_flows_for_node(node, known_ids))
    _log.debug("krb_trust_flows: synthesized %d trust edge(s)", len(flows))
    return tuple(flows)


def _krb_trust_flows_for_node(node: Node, known_ids: set[str]) -> list[Flow]:
    """Synthesize the trust-edge `Flow`(s) for one node's declared `trusts`."""
    manifest = krb_manifest_for(node)
    if manifest is None:
        return []
    flows: list[Flow] = []
    for trust in manifest.trusts:
        attrs = ("krb_trust",) if trust.transitive else ("krb_trust", "krb_no_transit")
        flow_id = f"{_TRUST_FLOW_ID_PREFIX}{node.id}:{trust.target}"
        flows.append(Flow(id=flow_id, src=node.id, dst=trust.target, attrs=attrs))
        if trust.direction == "two-way" and trust.target in known_ids:
            # Synthesize the reverse edge too so a single declaration
            # on ONE side of a two-way trust is enough (docs/strata/
            # krb.md#domain-trust-lattice) -- no requirement that the
            # target realm node redeclare the same trust back.
            reverse_id = f"{_TRUST_FLOW_ID_PREFIX}{trust.target}:{node.id}"
            flows.append(
                Flow(
                    id=reverse_id,
                    src=trust.target,
                    dst=node.id,
                    attrs=attrs,
                )
            )
    return flows


# frob:doc docs/strata/krb.md#surface-grammar
# frob:tests tests/unit/strata/test_krb.py::TestFlowAuthVia.test_read kind="unit"
def flow_authenticates_via(flow: Flow) -> str | None:
    """Read a `Flow`'s `authenticates_via` ticket kind back off its attrs.

    Returns the raw `tgt`/`st` ident the parser accepted (`strata-core/src/
    parse.rs::parse_flow`), or `None` when the flow declares no Kerberos
    crossing at all. Mirrors `krb_manifest_for`'s "no attr, no fact"
    contract for the node-level constructs above.
    """
    for attr in flow.attrs:
        if attr.startswith(_TICKET_PREFIX):
            return attr[len(_TICKET_PREFIX) :]
    return None
