# strata std.host -- OS-layer modeling (T-0255)

<!-- frob:ticket T-0255 -->

One sentence: `std.host` lets a node/store declare the OS-layer facts a
real deployment needs -- a dedicated service user, a systemd unit
binding, filesystem ownership, and listening ports -- as first-class
strata vocabulary, elaborated into one platform-tagged `HostManifest`
every deploy-epoch ticket (T-0254's children) reads instead of
re-deriving.

This is the FOUNDATION ticket of the deploy epic. It ships the grammar,
the elaborator desugar, and the `HostManifest` read-back model only --
**no generator** (T-0256 turns a manifest into an actual systemd unit
file / useradd script), **no proofs** (T-0257 model-checks flows between
`runs_as` service-user identities the way any other trust-lattice
crossing is checked). Both are explicitly out of scope here.

## Surface grammar

```
node api : trusted {
    clearance Internal;
    runs_as "api-svc";
    unit;
    owns "/etc/api" "0644";
    owns "/var/lib/api" "0750";
    listens 8080;
    listens 8443;
}
```

- `runs_as "svc-name"` -- names the dedicated OS service user the deploy
  generator (T-0256) will create for this node: system-scoped, no login
  shell, no home directory unless a future clause declares one. STRING
  (not IDENT), matching the `code`/`may`/`carries` precedent (T-0132/
  T-0154) for atoms that commonly carry `-`. At most one per node; a
  repeated clause overwrites, the same as `clearance`.
- `unit` -- a bare marker (mirrors `managed`'s shape, T-0172): this
  node's process is modeled as a systemd unit. Hardening directives
  (`NoNewPrivileges`, `ProtectSystem=strict`, `PrivateTmp`,
  `CapabilityBoundingSet` derived from `may` capabilities, and the
  existing seccomp exporter (`_export.py::export_seccomp`) wired in as
  `SystemCallFilter`) are DERIVED by the generator from the rest of the
  model, not declared here -- this marker only records that the binding
  applies.
- `owns "PATH" "MODE"` -- a filesystem path this node's service user
  owns, with an explicit octal mode. Both STRING (PATH carries `/`, MODE
  is an opaque atom). Repeatable: a node may own more than one path.
- `listens PORT` -- a TCP/UDP port this node's unit binds a socket to.
  NUMBER, matching `capacity`'s replicas-bound convention. Repeatable.

`store` accepts the identical four clauses (a store is a node too,
docs/strata/surface.md#key-construct-semantics) -- `strata-core/src/
parse.rs`'s `parse_node`/`parse_store` implement them with matching
shapes and matching doc comments.

## Elaboration: attr desugar, not a new kernel primitive

Charter law 1 (a vocabulary is a pure function surface -> kernel facts)
holds here exactly as it does for `code`/`may`/`carries`/`managed`:
`std.host` adds nothing to `KernelModel`/`Node`. Each clause desugars to
a plain `Node.attrs` string, in `src/frob/strata/_host.py::host_attrs`
-- the ONE place the encoding is written, imported by both
`_elaborate.py::_elaborate_node` (node) and `_infra.py::
_elaborate_store` (store) so the convention cannot desync between the
two callers:

| Clause | Attr |
|---|---|
| `runs_as "X"` | `runs_as=X` |
| `unit` | `unit` |
| `owns "P" "M"` | `owns=P:M` (one per entry) |
| `listens N` | `listens=N` (one per entry) |

## HostManifest

`src/frob/strata/_host.py::host_manifest_for(node)` reads a `Node`'s
attrs (of either origin, node- or store-derived) back into one typed
`HostManifest`:

```python
class HostManifest(BaseModel):
    platform: HostPlatform     # discriminator; only LINUX_SYSTEMD today
    runs_as: str | None
    is_unit: bool
    owns: tuple[HostOwns, ...]  # HostOwns(path, mode)
    listens: tuple[int, ...]
```

Returns `None` when the node declares no std.host construct at all --
distinguishing "no OS-layer facts" from "an OS-layer declared with
nothing set" (an empty-but-present manifest would be a different claim).

`platform` is a discriminator reserved for T-0261 (windows): only
`HostPlatform.LINUX_SYSTEMD` is produced by this ticket's grammar and
elaborator, but T-0256 (generator), T-0257 (flow proofs), T-0258
(conformance checker), and T-0259 (VM auditor) must all already branch
on it -- adding a second platform value later is additive, not a
rewrite of every consumer. This is the "one manifest, no duplication"
requirement from T-0254's spec: four downstream tickets read one parse
of the attr convention, not four independent re-parsings.

## OS users and the trust lattice

T-0254's spec calls for OS users to "join the trust lattice, so flows
between service users are model-checked like any other flow." Today
that participation is exactly the `runs_as=<name>` attr any future flow
machinery can already read off a `Node` like any other attr -- there is
no dedicated lattice plumbing in this ticket (no proofs, per the
explicit scope cut above). Actually mapping `runs_as` identities onto
trust-lattice participants with their own crossing obligations is
T-0257's job.

## Scope boundary (what is NOT built here)

- No generator: `HostManifest` -> actual `useradd`/`systemd` unit file /
  filesystem `chmod`/`chown` script is T-0256.
- No proofs: service-user-to-service-user flow model-checking is T-0257.
- No conformance checker (declared manifest vs. what a running host
  actually has) -- T-0258.
- No VM auditor -- T-0259.
- No second `HostPlatform` member (windows) -- T-0261; the discriminator
  is designed for it, but only linux/systemd is implemented here.

## See also

- `docs/strata/surface.md#node-grammar` -- the node/store grammar this
  vocabulary extends.
- `docs/strata/surface.md#key-construct-semantics` -- "a store is a node
  too", the precedent every store-side clause here follows.
- `src/frob/strata/_host.py` -- `host_attrs`, `host_manifest_for`,
  `HostManifest`, `HostOwns`, `HostPlatform`.
- `tests/unit/strata/test_litmus_host.py` -- parse -> elaborate ->
  `host_manifest_for` round trip over the declared/undeclared litmus
  pair.
