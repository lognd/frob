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
**no generator** (T-0257 turns a manifest into an actual systemd unit
file / useradd script), **no isolation proofs** (T-0256,
#movement-impossibility-proofs below, model-checks lateral/vertical
movement between `runs_as` service-user identities the way any other
trust-lattice crossing is checked). Both are explicitly out of scope
here.

> Note (T-0256 landing correction): earlier drafts of this doc named
> T-0256 as "the generator" and T-0257 as "flow proofs" -- the ticket
> ledger (`tickets.md`) shipped with the OPPOSITE assignment (T-0256 =
> movement-impossibility proofs/HOST001/HOST002, T-0257 = `frob deploy
> generate`). This doc now matches `tickets.md`, the authoritative
> source.

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
  generator (T-0257) will create for this node: system-scoped, no login
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
elaborator, but T-0256 (isolation proofs), T-0257 (generator), T-0258
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
no dedicated lattice plumbing in `std.host` itself (no proofs live
here). T-0256 (below) is that follow-up: it does not add lattice
plumbing either, deriving its findings directly from `HostManifest`
intersection instead.

## Movement-impossibility proofs

The red-team scenario -- "one service user's process is compromised,
what can it reach?" -- as a first-class, DEMANDED obligation the moment
a model declares 2+ `runs_as` service users. `src/frob/strata/
_host_isolation.py` implements two rules, both DERIVED from
`HostManifest` intersection (never a hand-written per-pair/per-user
table):

- **HOST001 (lateral movement)**, per DISTINCT service-user PAIR: no
  shared writable filesystem path, no shared listening port reachable
  across users without a declared `Flow` bridging their nodes, and (an
  honest gap -- see below) no shared OS group.
- **HOST002 (vertical movement)**, per service user: no setuid path
  owned, no sudoers grant (honest gap), no root-run unit whose owned
  paths this user can write to, and no write access to a path a
  higher-trust node also owns.

### The honest gap

`std.host`'s grammar has no OS-group or sudoers-grant vocabulary (T-0256
is scoped to `src/frob/strata/**`, not `strata-core/**`, so it cannot add
either). Deny-by-default (charter law 2): the `shared-group` and
`sudoers` sub-targets UNCONDITIONALLY fire until an operator writes an
explicit `waive "HOST001:shared-group" reason="..."` /
`waive "HOST002:sudoers" reason="..."` clause, or T-draft-7b5b5541 (filed
by T-0256, `tickets.md`) adds the missing grammar. `setuid` needs no new
grammar at all -- a 4-digit `owns "PATH" "4755"` mode already carries the
setuid bit.

### Waiver discipline

HOST001/HOST002 are multi-instance-per-node (one finding per pair
sub-target / per user sub-target) -- `_host_isolation.py::
HOST_MULTI_INSTANCE_WAIVER_FAMILIES` requires the SAME `RULE:SUBTARGET`
waiver shape T-0174 established for SYS100/SYS101/THREAT002/THREAT003
(`_waive.py`), run through the SAME `apply_waivers` channel
(`evaluate_host_isolation_waived`). A HOST001 pair finding is attributed
to the alphabetically-earlier user of the pair -- see `evaluate_host_
isolation_waived`'s `target_of` docstring for why a duplicate waiver on
the peer's node correctly reports STALE.

### Compromised-service-owner threat catalog

`_host_isolation.py::COMPROMISED_OWNER_CATALOG` adds CWE-284 (improper
access control, HOST001's class), CWE-269 (improper privilege
management, HOST002's class), and CWE-522 (insufficiently protected
credentials) to a SEPARATE `compromised-owner-baseline` view
(`COMPROMISED_OWNER_VIEWS`) -- never appended to `_threat.py::
CWE_CATALOG`/`VIEWS`, the same separate-view precedent
`QUALITY_CATALOG`/`CWE_TOP_25_CATALOG` set.

### Compromised-user scenario

`_scenarios.py::build_compromised_user_scenario` builds the red-team
scenario itself: every node declaring `runs_as=<user>` is downgraded via
the EXISTING `SetTrust` rewrite, and one `NoFlow(src="foreign",
dst=<node>)` claim is asserted per node OUTSIDE the user's manifest
slice -- `evaluate_scenarios` re-checking this scenario proves the
compromise's blast radius is exactly that user's own slice, no wider.

**Review-round fix (vacuity):** a `NoFlow` claim is only ever proved or
refuted over `_facts.py::FactBase.reachable`'s DECLARED-`Flow` closure --
it has no dependency on `HostManifest` ownership by itself. Two users
sharing a writable path with NO declared app `Flow` between them would
make HOST001 correctly fire (`shared-writable-path`) while the SAME
model's blast-radius claim vacuously reported PROVED -- false assurance,
caught in review. The fix: `_host_isolation.py::host_movement_flows`
derives the SAME sharing relations HOST001 detects (shared writable
path, shared reachable socket) as synthetic `Flow` facts, and the
scenario builder wraps each in the new `AddFlow` rewrite (`_models.py`)
so the closure sees them too. `AddFlow` is scenario-scoped only -- it
never mutates the base `KernelModel`'s own declared flows, and reuses
the existing `Flow` fact shape (charter law 1: no new `strata_core`
closure primitive). The shared-writable-path adversarial case now
correctly REFUTES (`tests/unit/strata/test_host_isolation.py::
test_blast_radius_refutes_over_shared_writable_path_with_no_declared_flow`);
the disjoint hardened model still discharges (`test_blast_radius`).

### CLI reachability (T-0280)

`frob sys audit` (`_audit.py::evaluate_exhaustiveness`) folds HOST001/
HOST002 into its normal `FamilyGap` stream under the fixed `"host"`
family/`"model"` view -- `evaluate_host_isolation_waived`'s own T-0174
waiver channel is honored as-is (its `.kept` is already post-waiver, its
`.waived`/`.stale` are folded straight into the report). Additionally, one
`build_compromised_user_scenario` is auto-generated and evaluated PER
`runs_as` service user (the same "desugar to an auto-generated scenario"
shape `_crash.py` uses for `on crash` contracts) -- a refuted blast-radius
claim surfaces as a `HOST-BLAST` gap under the `"blast-radius"` view. A
real repo now sees the full isolation verdict (proved or gaps named) from
one command; before this, neither function had any caller reaching them
from the CLI at all (a hand-written harness was the only way to invoke
them).

## The deploy generator

<!-- frob:ticket T-0257 -->

`frob deploy generate` (`docs/commands/deploy.md`, `src/frob/deploy/`)
compiles every node/store's `HostManifest` into three Linux/systemd bash
scripts -- `install.sh` (idempotent by construction: every step is
check-then-apply), `status.sh` (per-unit active/enabled state plus a
listen-port probe), and `uninstall.sh` (removes EXACTLY the manifest's
own units/users/owned paths). A generated unit's `CapabilityBoundingSet=`
and `SystemCallFilter=` are BOTH derived from the same `may`-capability
kind join `src/frob/strata/_export.py::export_seccomp` already uses for
its seccomp profiles (`node_allowed_syscalls`, `node_may_kinds`) -- one
join, two renderings, never a second independently maintained mapping.

Every generated script's header carries a manifest digest; once a
`deploy/` directory exists, `frob check` runs an opt-in DEPLOY001 drift
check comparing the committed scripts against a fresh regeneration from
the current model (`docs/commands/deploy.md#deploy001-the-drift-lock`).
Full detail, including the honest OS-users-vs.-trust-lattice scope cut
this generator inherits unchanged from this ticket, lives in
`docs/commands/deploy.md`.

## DEPLOY002/DEPLOY003: conformance

<!-- frob:ticket T-0258 -->

DEPLOY001 (above) catches a hand-edit by byte-diffing a committed script
against a fresh regeneration -- but that check is only as strong as its
digest header: an operator (or an attacker with commit access) can hand-
append or hand-remove a step and never re-run `frob deploy generate`
again, and DEPLOY001 still fires, but only ever says "does not match
regeneration", never WHY. `frob.deploy._conform` (`src/frob/deploy/
_conform.py`) gives the structural why by parsing each committed script's
actual MUTATION SURFACE -- the STRUCTURED set of `useradd`/`groupadd`/
`userdel`/`groupdel`/`mkdir`/`install`/`cp`/`chown`/`chmod`/`rm -f`/
`rm -rf`/`systemctl enable|disable|start|stop`/unit-file-heredoc
invocations and their exact targets, extracted by anchoring to the exact
check-then-apply shapes `_generate.py` renders (never a blind grep --
heredoc unit-file bodies' unquoted `systemd` directives never false-
positive as a mutation) -- and comparing it bidirectionally against the
EXACT set `HostManifest` declares:

- **DEPLOY002** (extra mutation, not declared): the script performs a
  mutation the manifest does not declare -- a smuggled extra user, path,
  or unit. This is the red-team-relevant direction: it fires even when
  the rest of the script is byte-identical to a real regeneration, so
  bypassing `frob deploy generate` and hand-appending one rogue
  `useradd` still fails `frob check`.
- **DEPLOY003** (manifest entry, no mutation implements it): a declared
  `runs_as`/`owns`/`unit` entry that the script implements no mutation
  for -- an incomplete install (a declared `owns` path never `mkdir`/
  `chown`/`chmod`'d) or incomplete uninstall (a declared service user
  never `userdel`'d).

`install.sh` and `uninstall.sh` are each checked independently against
the SAME declared set, so a tamper isolated to one script (e.g. removing
uninstall's `userdel` while leaving install untouched) is reported
against the script it actually touched. This is the tie that makes the
committed scripts part of the provable architecture rather than
artifacts sitting beside it: a `HostManifest` change with no matching
script edit fails DEPLOY003, and a script edit with no matching
`HostManifest` change fails DEPLOY002, regardless of whether DEPLOY001's
digest happens to still line up.

Wired into `frob check` the same "extra stage, not `frob.gates`'s
pluggable job table" shape DEPLOY001 uses (`frob.app.check_runner.
_deploy_conformance_result`). Opt-in on `deploy/` existing, same posture
as DEPLOY001.

## Scope boundary (what is NOT built here)

- No live-host conformance checker (declared manifest vs. what a
  RUNNING host actually has, as opposed to the committed scripts) -- 
  T-0259's VM auditor.
- No second `HostPlatform` member (windows) -- T-0261; the discriminator
  is designed for it, but only linux/systemd is implemented here
  (T-0257's generator is the same linux/systemd-only scope).
- No OS-group / sudoers grammar (T-draft-7b5b5541, filed by T-0256) --
  the honest gap #the-honest-gap above.

## See also

- `docs/commands/deploy.md` -- `frob deploy generate`, DEPLOY001, and the
  T-0257 scope/honesty notes.
- `docs/strata/surface.md#node-grammar` -- the node/store grammar this
  vocabulary extends.
- `docs/strata/surface.md#key-construct-semantics` -- "a store is a node
  too", the precedent every store-side clause here follows.
- `src/frob/strata/_host.py` -- `host_attrs`, `host_manifest_for`,
  `HostManifest`, `HostOwns`, `HostPlatform`.
- `src/frob/strata/_host_isolation.py` -- HOST001/HOST002,
  `HostIsolationViolation`, `evaluate_host_isolation_waived`,
  `COMPROMISED_OWNER_CATALOG`.
- `src/frob/strata/_scenarios.py::build_compromised_user_scenario` --
  the compromised-owner red-team scenario builder.
- `tests/unit/strata/test_litmus_host.py` -- parse -> elaborate ->
  `host_manifest_for` round trip over the declared/undeclared litmus
  pair.
- `tests/unit/strata/test_litmus_host_isolation.py` -- the shared-user
  VULN / isolated HARDENED litmus pair for HOST001/HOST002.
