# strata std.krb -- Kerberos/AD domain trust modeling (T-0262)

<!-- frob:ticket T-0262 -->

One sentence: `std.krb` lets a node declare the Kerberos/Active-Directory
facts a real domain-joined deployment needs -- realm/KDC identity, an SPN
bound to a `runs_as` service account (T-0255), a typed delegation
declaration, and cross-realm domain trust -- as first-class strata
vocabulary, elaborated into node attrs plus a synthesized `Flow` edge so
the EXISTING reach/noflow closure machinery can answer cross-realm
reachability questions without a dedicated Kerberos graph.

This is the auth pillar of the deploy epic (T-0254), built on T-0255's
`HostManifest`/`runs_as` (SPNs bind to that same principal). It ships the
grammar, the elaborator desugar, the `KrbManifest` read-back model, and
the domain-trust-lattice synthesis only -- **no delegation-abuse
obligations** (T-0263 -- flagging unconstrained delegation reachable from
an untrusted node, an RBCD chain crossing a trust boundary, etc.). That is
explicitly out of scope here; `KrbManifest.delegation` is a typed fact,
unexamined by any obligation rule in this ticket.

## Surface grammar

```
node corp_kdc : trusted {
    clearance Internal;
    realm "CORP.EXAMPLE";
    kdc;
    trusts partner_kdc direction "two-way" transitive;
}

node partner_kdc : trusted {
    clearance Internal;
    realm "PARTNER.EXAMPLE";
    kdc;
}

node app : trusted {
    clearance Internal;
    realm "CORP.EXAMPLE";
    runs_as "app-svc";
    spn "HTTP/app.corp.example@CORP.EXAMPLE";
    delegation constrained target "HTTP/backend.corp.example@CORP.EXAMPLE";
}

node backend : trusted {
    clearance Internal;
    realm "PARTNER.EXAMPLE";
}

flow app_to_backend: app -> backend {
    authenticates_via st;
}
```

- `realm "REALM.NAME"` -- names the Kerberos realm / AD domain this node
  participates in (or, paired with `kdc`, represents). STRING, not IDENT,
  since a realm name commonly carries `.` (same `runs_as`/`code`
  precedent). At most one per node; a repeated clause overwrites, the
  same as `clearance`.
- `kdc` -- a bare marker (mirrors `unit`'s shape, T-0255): this node is
  the Key Distribution Center for its `realm`. Both realm/KDC nodes are
  ordinary trust-lattice `Node`s -- no dedicated node kind exists, matching
  charter law 1.
- `spn "SPN/value@REALM"` -- one or more service principal names bound to
  this node's `runs_as` service account (T-0255's principal). STRING,
  repeatable, same shape as `code`/`carries`.
- `delegation none | constrained | rbcd | unconstrained [target "SPN"]*`
  -- the crown-jewel modeling target: the classic lateral-movement vector,
  now a first-class typed declaration instead of an invisible AD
  attribute. `target` is only meaningful under `constrained`; a `target`
  clause under any other kind is an elaboration-time error
  (`_elaborate.py::_validate_krb`), not a silent drop (charter law 2).
  Repeatable `target` entries let one node declare a constrained-
  delegation SPN-set.
- `trusts IDENT [direction "one-way"|"two-way"] [transitive]` -- a domain
  trust edge from THIS realm node to `IDENT`, another node's id (must be
  declared; a dangling reference is an elaboration-time error, mirroring
  `panics_contained_by`'s precedent). `direction` defaults to `"one-way"`
  (the safer default per charter law 2: a trust must be explicitly
  widened to two-way, never silently assumed bidirectional). Repeatable:
  a realm may trust more than one other realm.

  <!-- frob:invariant INV-031 -->
- `authenticates_via tgt|st` -- a `flow`-level clause marking that flow as
  crossing a Kerberos authentication boundary (a ticket-granting-ticket
  exchange or a service-ticket exchange). IDENT, closed to `tgt`/`st`
  today (a third ticket kind is a grammar extension, not an elaborator
  one).

None of the above is store-scoped in this pass (unlike `std.host`'s
`runs_as`/`unit`/`owns`/`listens`, which `parse_store` also accepts) --
see #scope-boundary below for why that is an explicit, disclosed cut
rather than an oversight.

## Elaboration: attr + one synthesized Flow, not a new kernel primitive

Charter law 1 holds here exactly as it does for `std.host`: `std.krb`
adds nothing to `KernelModel`/`Node`. Every node-level clause desugars to
a plain `Node.attrs` string via `src/frob/strata/_krb.py::_krb_attrs` --
the ONE place that encoding is written, called from `_elaborate.py::
_elaborate_node` the same way `host_attrs` is:

| Clause | Attr |
|---|---|
| `realm "R"` | `krb_realm=R` |
| `kdc` | `krb_kdc` |
| `spn "S"` | `krb_spn=S` (one per entry) |
| `delegation K` | `krb_delegation=K` |
| `target "S"` | `krb_delegation_target=S` (one per entry) |
| `trusts T direction "D" transitive` | `krb_trust=T:D:True\|False` |
| `authenticates_via K` (on `flow`) | `krb_ticket=K` |

`trusts` is the ONE exception that also touches `KernelModel.flows`: a
domain trust is a cross-realm RELATIONSHIP, not a single node's fact, so
`_elaborate.py::elaborate` additionally calls `_krb.py::
krb_trust_flows(nodes)` after nodes are elaborated, which synthesizes one
`Flow(id="krb-trust:<src>:<dst>", attrs=("krb_trust",))` per declared
trust -- TWO flows (both directions) when `direction == "two-way"`, so a
single declaration on one side of a two-way trust is enough; the target
realm node never has to redeclare the same trust back. This happens at
elaboration time, unconditionally, NOT as a scenario rewrite (`AddFlow`)
-- a domain trust is a standing fact of the design, present in every
scenario's base model, not a counterfactual one scenario injects.

Because these are ordinary `Flow` facts, the EXISTING `noflow`/`reach`
claim machinery walks them with zero changes: `assert x: noflow
corp_realm_node -> untrusted_partner` (say, an unlisted or since-revoked
partner) proves/refutes over the SAME closure the rest of the kernel
already computes. A trust declared WITHOUT `transitive` gets the
`krb_no_transit` attr on its synthesized `Flow` (T-0282), which
`FactBase.reachable` reads into a terminal-edge flag the shared kernel BFS
(`strata-core/src/lib.rs::reachable`) enforces -- see #domain-trust-
lattice below for the full multi-hop semantics.

## KrbManifest

`src/frob/strata/_krb.py::krb_manifest_for(node)` reads a `Node`'s attrs
back into one typed `KrbManifest`:

```python
class KrbManifest(BaseModel):
    realm: str | None
    is_kdc: bool
    spns: tuple[str, ...]
    delegation: KrbDelegationKind | None   # none|constrained|rbcd|unconstrained
    delegation_targets: tuple[str, ...]
    trusts: tuple[KrbTrust, ...]           # KrbTrust(target, direction, transitive)
```

Returns `None` when the node declares no std.krb construct at all --
distinguishing "no Kerberos-layer facts" from "a Kerberos layer declared
with nothing set" (mirrors `HostManifest`'s same contract exactly).

`src/frob/strata/_krb.py::flow_authenticates_via(flow)` is the flow-level
read-back half: returns the raw `tgt`/`st` ticket kind, or `None` when the
flow declares no Kerberos crossing.

## Platform neutrality

Unlike `HostManifest`, `KrbManifest` carries NO platform discriminator.
An SPN and a `runs_as` service account compose identically whether the
account is an MIT/Heimdal keytab principal (linux) or a gMSA/AD service
account (T-0261, windows) -- the Kerberos protocol layer this vocabulary
models does not differ in SHAPE between the two backends, only in the
deploy-time MECHANISM (kinit/keytab install vs. `Set-ADServiceAccount`)
that a later generator ticket would render, not this model. `_krb.py`
never imports or branches on `HostPlatform` for exactly this reason.

## Domain trust lattice

Realm/KDC nodes are ordinary trust-lattice `Node`s (they carry a `trust`
level like any node); `trusts` edges are ordinary `Flow`s. There is no
second, krb-specific lattice living beside `_models.py::TRUST` -- "join
the lattice" (T-0254's spec language) means exactly this: cross-realm
reachability answers come from the SAME `FactBase.reachable` closure walk
every other `noflow`/`reach` claim already uses, not a bespoke traversal.

### Non-transitive trusts are terminal edges (T-0282)

`KrbTrust.transitive` is a real, typed field, and `direction`/`transitive`
both round-trip through parse -> elaborate -> `krb_manifest_for` exactly
as declared. It also changes how `FactBase.reachable` walks the
synthesized trust `Flow`s: `strata_core::reachable` (the shared Rust BFS
every `noflow`/`reach` claim in the kernel uses) has a terminal-edge
concept in its `Edge` type (`strata-core/src/lib.rs`, 5th field
`transitive`) -- an edge with `transitive=false` discovers its `dst` (one
hop is always correct) but is never enqueued for further expansion, so it
cannot become a middle link in a longer chain. `_krb.py::krb_trust_flows`
puts the `krb_no_transit` attr on a trust's synthesized `Flow` exactly
when `KrbTrust.transitive` is `False`; `_facts.py::FactBase.reachable`
reads that attr into the kernel's `transitive` edge field.

Concretely: a chain of realm nodes `a --trusts--> b --trusts--> c`, with
BOTH trusts declared `transitive`, yields `reach(a, c) = True` (correct,
unchanged multi-hop chaining). The SAME chain with NEITHER trust declared
`transitive` yields `reach(a, c) = False` -- `b` is reachable directly
(single-hop reach through a non-transitive edge is always correct) but the
chain stops there. This was caught in review (T-0262 round 2) via the
reviewer's own reproduction, tracked and closed as T-0282 -- see
`tests/unit/strata/test_krb.py::TestTrustChainReachability` for the
permanent regression coverage and `tests/unit/strata/test_facts.py::
TestClosure.test_krb_no_transit_attr_stops_chaining_past_that_hop` /
`strata-core/src/lib.rs::tests::non_transitive_edge_is_a_terminal_hop` for
the kernel-level coverage.

`direction` (one-way vs. two-way, which trust flows get synthesized) and
`transitive` (whether a trust chains past its own hop) are both honored
correctly today -- any T-0263/T-0264 containment reasoning over krb trust
chains may rely on `transitive=False` to bound cross-realm reachability.

## Movement proofs

T-0263 is the examiner `_krb.py`'s module docstring promised: `_krb_
movement.py` implements four rules, every one DERIVED from `KrbManifest`
(never a hand-written per-node table), the KRB sibling of HOST001/
HOST002's compromised-service-owner family (`docs/strata/host.md
#movement-impossibility-proofs`, T-0256):

- **KRB001 (unconstrained delegation)** -- any node declaring `delegation
  unconstrained` is a hard finding: a compromise of that node can
  impersonate ANY user to ANY service in the realm, the worst
  lateral+vertical vector std.krb can represent. Fires unconditionally,
  deny-by-default, until re-declared constrained/rbcd or waived with a
  written accepted-risk reason.
- **KRB002 (Kerberoasting exposure)** -- every declared `spn` is presumed
  roastable. `std.krb` has no vocabulary distinguishing a gMSA/machine-
  account principal from a human-memorable one (that grammar lives in
  `strata-core/src/parse/mod.rs`, outside T-0263's `src/frob/strata/**` scope,
  the identical cut T-0256 hit before T-0272 added `group`/`sudoers`), so
  this is an always-fire honest gap exactly like HOST002's pre-T-0272
  `sudoers` sub-target -- an operator either accepts the finding or waives
  it with a written gMSA/machine-account attestation.
- **KRB003 (constrained-delegation blast radius)** -- for a node with
  `delegation constrained`, the transitive closure of its `target` SPNs is
  followed over every OTHER constrained-delegation node's own targets
  (S4U2Proxy chaining, `_krb_movement.py::_delegation_reach_higher_
  trust`), never just the immediate `target` list, and must never reach a
  node whose trust is strictly higher than the delegating node's own. Each
  reached higher-trust node is its own finding with a full witness path.
- **KRB004 (cross-realm containment)** -- for every node declaring a
  `realm`, no OTHER realm's node may be reachable via `_facts.py::
  FactBase.reachable` (the SAME closure engine every `noflow` claim uses,
  walking `model.flows` INCLUDING the krb-trust `Flow`s `krb_trust_flows`
  already synthesizes at elaboration time) whose trust is strictly higher
  AND whose reaching path actually transits a `krb_trust`-tagged edge --
  an escalation reached by an ordinary declared app `Flow` is a different
  obligation's business, not this rule's undeclared-trust-path claim.

Every rule is multi-instance-per-node (one KRB002 finding per SPN, one
KRB003/KRB004 finding per distinct higher-trust node reached) --
`_krb_movement.py::KRB_MULTI_INSTANCE_WAIVER_FAMILIES` requires the SAME
`RULE:SUBTARGET` waiver shape T-0174 established, run through the SAME
`_waive.py::apply_waivers` channel `evaluate_host_isolation_waived` uses
(`evaluate_krb_movement_waived`), each rule scoped to its own family so
one rule's waiver can never silently swallow another's finding.

### Compromised-domain-principal threat catalog

`_krb_movement.py::KRB_MOVEMENT_CATALOG` adds CWE-269 (improper privilege
management, KRB001/KRB003's escalation-via-delegation class), CWE-284
(improper access control, KRB004's cross-realm class), and CWE-522
(insufficiently protected credentials, KRB002's roastable-SPN class) to a
SEPARATE `krb-movement-baseline` view (`KRB_MOVEMENT_VIEWS`) -- never
appended to `_threat_catalog_cwe.py::CWE_CATALOG`/`VIEWS`, the same separate-view
precedent `COMPROMISED_OWNER_CATALOG` set for HOST001/HOST002.

### Compromised-krb-principal scenario

`_scenarios.py::build_compromised_krb_scenario` reuses the T-0073
scenario engine (the SAME `SetTrust`/`AddFlow`/`NoFlow` primitives
`build_compromised_user_scenario` already reuses for HOST001/HOST002) to
prove a compromised krb-bound node's blast radius is bounded by exactly
what its OWN delegation grants: unconstrained delegation materializes a
synthetic edge to EVERY other node (the true worst-case reach KRB001
names), constrained delegation materializes edges only to its resolved
`target` SPNs' owning nodes. A `NoFlow` claim per node outside that reach
set is refuted the moment the closure actually gets there -- not
vacuously proved over an unrelated declared-flow graph, guarded against
the identical way `_scenarios.py`'s module docstring records T-0256's
review-round REJECT fix.

## Scope boundary (what is NOT built here)

- **No RBCD-chain-vs-trust-boundary cross-check** (disclosed cut,
  T-0263): KRB003 follows constrained-delegation chains, but an RBCD
  (`delegation rbcd`) node's blast radius against declared trust
  boundaries is not separately modeled -- `rbcd` nodes are read (typed
  enum value) but no rule yet examines them the way `constrained` is
  examined by KRB003. Filed as follow-on work rather than silently
  expanding this ticket's scope.
- **No `frob sys audit` wiring** (disclosed cut, T-0263, mirrors T-0280's
  staged rollout for HOST001/HOST002): `evaluate_krb_movement_waived`/
  `build_compromised_krb_scenario` are built and sound but have no caller
  reaching them from `_audit.py::evaluate_exhaustiveness` yet -- exactly
  the gap T-0280 closed for HOST001/HOST002 after T-0256, filed
  separately rather than silently widening this ticket's scope.
- **No store-level std.krb clauses.** `std.host` extended `runs_as`/
  `unit`/`owns`/`listens` to both `parse_node` and `parse_store` (a store
  is a node too). This ticket adds `realm`/`kdc`/`spn`/`delegation`/
  `trusts` to `parse_node` only -- a domain-joined datastore (e.g. an
  AD-integrated SQL Server with its own SPN) cannot declare std.krb facts
  today. Disclosed cut, not an oversight: extending `parse_store` the
  identical way `std.host` did is small, well-precedented follow-up work,
  filed separately rather than silently expanding this ticket's scope.
- **No generator/deploy-time mechanism** (kinit invocation, keytab
  provisioning, `Set-ADServiceAccount`/gMSA install) -- mirrors
  `std.host`'s own "manifest only, T-0257 is the generator" scope cut.

## See also

- `docs/strata/host.md` -- `std.host`'s `HostManifest`/`runs_as`, the
  foundation this vocabulary's SPN binding builds on.
- `docs/strata/surface.md#node-grammar-implemented-t-0132-closes-the-codemay-gap-t-0136-adds-on-deploy-t-0154-adds-carries-t-0172-adds-managed-t-0174-adds-waive` -- the node grammar this
  vocabulary extends.
- `docs/strata/kernel.md#data-models` -- `Node`/`Flow`, the two kernel
  primitives every std.krb clause desugars into.
- `src/frob/strata/_krb.py` -- `_krb_attrs`, `krb_manifest_for`,
  `krb_trust_flows`, `flow_authenticates_via`, `KrbManifest`,
  `KrbDelegationKind`, `KrbTrust`.
- `tests/unit/strata/test_krb.py` -- unit coverage for the desugar/
  read-back/synthesis functions against hand-built values.
- `tests/unit/strata/test_litmus_krb.py` -- parse -> elaborate ->
  `krb_manifest_for`/`krb_trust_flows`/`flow_authenticates_via` round trip
  over the declared/undeclared litmus pair.
- `src/frob/strata/_krb_movement.py` -- KRB001-004, `KrbMovementViolation`,
  `evaluate_krb_movement_waived`, `KRB_MOVEMENT_CATALOG`.
- `src/frob/strata/_scenarios.py::build_compromised_krb_scenario` -- the
  compromised-krb-principal red-team scenario.
- `tests/unit/strata/test_krb_movement.py` -- unit coverage for each rule
  and the compromised-krb scenario against hand-built values.
- `tests/unit/strata/test_litmus_krb_movement.py` -- parse -> elaborate ->
  `evaluate_krb_movement_waived` round trip over the vuln/hardened
  litmus pair.
