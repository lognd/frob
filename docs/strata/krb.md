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
a plain `Node.attrs` string via `src/frob/strata/_krb.py::krb_attrs` --
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
`_elaborate.py::_elaborate_module` additionally calls `_krb.py::
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
already computes, and a two-way transitive trust participates in
multi-hop reachability exactly like any other flow chain.

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

## Scope boundary (what is NOT built here)

- **No delegation-abuse obligations** (T-0263) -- no rule flags
  unconstrained delegation reachable from an untrusted node, no rule
  checks an RBCD chain against trust boundaries, no rule cross-references
  `delegation_targets` against declared SPNs elsewhere in the model. Every
  such check is exactly the crown-jewel obligation work T-0263 exists for;
  this ticket only makes the FACTS representable.
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
- `docs/strata/surface.md#node-grammar` -- the node grammar this
  vocabulary extends.
- `docs/strata/kernel.md#data-models` -- `Node`/`Flow`, the two kernel
  primitives every std.krb clause desugars into.
- `src/frob/strata/_krb.py` -- `krb_attrs`, `krb_manifest_for`,
  `krb_trust_flows`, `flow_authenticates_via`, `KrbManifest`,
  `KrbDelegationKind`, `KrbTrust`.
- `tests/unit/strata/test_krb.py` -- unit coverage for the desugar/
  read-back/synthesis functions against hand-built values.
- `tests/unit/strata/test_litmus_krb.py` -- parse -> elaborate ->
  `krb_manifest_for`/`krb_trust_flows`/`flow_authenticates_via` round trip
  over the declared/undeclared litmus pair.
