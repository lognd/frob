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
    group "deploy";
    sudoers "ALL=(root) NOPASSWD: /bin/systemctl restart api";
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
  is an opaque atom -- the grammar itself is platform-agnostic; see
  #hostmanifest below for where MODE is validated). Repeatable: a node
  may own more than one path.
- `listens PORT` -- a TCP/UDP port this node's unit binds a socket to.
  NUMBER, matching `capacity`'s replicas-bound convention. Repeatable.
- `group "NAME"` (T-0272) -- an OS group this node's service user is a
  member of. STRING, matching `runs_as`'s "opaque atom" reasoning (a
  group name may carry `-`). Repeatable: a service user may belong to
  more than one group. Owns-adjacent grammar shape.
- `sudoers "RULE"` (T-0272) -- a sudoers grant line held by this node's
  service user (e.g. `"ALL=(root) NOPASSWD: /bin/systemctl restart
  api"`). STRING, since a sudoers rule is free-form platform text, the
  same "opaque atom" reasoning as `may`/`carries`. Repeatable: a service
  user may hold more than one grant.

`store` accepts the identical six clauses (a store is a node too,
docs/strata/surface.md#key-construct-semantics) -- `strata-core/src/
parse.rs`'s `parse_node`/`parse_store` implement them with matching
shapes and matching doc comments.

## Windows surface grammar

<!-- frob:ticket T-0261 -->

T-0261 gives `std.host` a second platform, without growing `KernelModel`/
`Node` or splitting into two parallel models -- the same "ONE HostManifest,
platform-tagged" contract #surface-grammar above already reserved:

```
node api : trusted {
    clearance Internal;
    platform "windows";
    service_account "svc-api" gmsa;
    service;
    acl "C:\ProgramData\api" "BUILTIN\Administrators:FullControl";
    acl "C:\ProgramData\api\secrets" "svc-api:Modify:deny:no_inherit";
    pipe "\\.\pipe\api-control";
    listens 8443;
}
```

- `platform "windows"` -- the std.host platform discriminator. STRING, at
  most one per node; a repeated clause overwrites, mirroring `clearance`.
  Omitted means `HostPlatform.LINUX_SYSTEMD` (the pre-T-0261 default,
  backward compatible with every existing manifest); any value other than
  `"windows"` fails closed at `host_manifest_for` time with a plain
  `ValueError` (T-0261, the same defer-to-elaborator well-formedness
  discipline `owns` MODE/`listens` PORT already use).
- `service_account "NAME" [gmsa]` -- the Windows analog of `runs_as`:
  names a dedicated low-privilege local service account, or -- with the
  trailing bare `gmsa` marker -- a group Managed Service Account for
  domain-joined hosts. STRING, same "opaque atom" reasoning as `runs_as`.
  At most one per node; a repeated clause overwrites. The deploy
  generator (T-0257's windows follow-up, not built here) is expected to
  derive the hardening posture T-0254's spec calls for from this and the
  rest of the model -- no interactive-logon right, deny-network-logon
  where possible, `SeDenyBatchLogonRight` -- the same way `unit`'s
  hardening directives are derived, not declared.
- `service` -- a bare marker (mirrors `unit`'s shape): this node's
  process is modeled as a Windows Service Control Manager (SCM) service.
  Hardening equivalents (service SID type restricted, a required-
  privileges allowlist derived from `may` capabilities, protected-process
  where applicable) are DERIVED by the generator from the rest of the
  model, not declared here -- this marker only records that the binding
  applies, the same scope cut `unit` made for systemd.
- `acl "PATH" "RULE"` -- the Windows analog of `owns`: an NTFS path this
  node's service account has an explicit DACL entry for. Richer than a
  3-octal POSIX mode by design -- RULE is a `PRINCIPAL:RIGHTS[:deny]
  [:no_inherit]` atom (#hostacl-rule-validation below) expressing a
  specific principal's rights grant, an optional deny ACE (vs. the
  default allow), and an optional deny-inheritance marker. Both STRING
  (PATH commonly carries `:` for a drive letter and `\` path separators;
  RULE is an opaque atom validated by the elaborator, not the grammar).
  Repeatable: a node may declare more than one ACL entry.
- `pipe "NAME"` -- a named pipe this node's service listens on. STRING,
  since a pipe name commonly carries `\` (e.g. `\\.\pipe\api-control`).
  Repeatable. Additive to, not a replacement for, the already-platform-
  agnostic `listens` PORT surface above -- a Windows firewall port rule is
  the same "a bound socket, and the firewall opening for it" concept a
  linux `listens` clause already covers, so T-0261 reuses `listens`
  unchanged rather than adding a second, duplicate port grammar (charter
  law 5: no duplication).

`store` accepts the identical five Windows clauses, same "a store is a
node too" precedent #surface-grammar above already established.

### HostAcl RULE validation

`HostAcl.rule` is validated (a pydantic `field_validator`, mirroring
`HostOwns._validate_mode`'s fail-closed discipline) to be a well-formed
`PRINCIPAL:RIGHTS[:deny][:no_inherit]` atom: PRINCIPAL and RIGHTS may not
be empty, and any trailing flag after RIGHTS must be exactly `deny` or
`no_inherit` -- `"Everyone:FullControl"`, `"svc-api:Modify:deny"`, and
`"svc-api:Modify:deny:no_inherit"` all pass; `"Everyone:"` (empty RIGHTS),
`"FullControl"` (no `:` at all), and `"Everyone:FullControl:bogus"` (an
unrecognized flag) are all rejected. The attr encoding itself uses `|`,
not `:`, to separate PATH from RULE (`acl=<path>|<rule>`) -- unlike a
POSIX `owns` path, a Windows PATH routinely contains `:` itself (a drive
letter), and RULE contains `:` internally too, so a naive first-colon
partition would silently split the drive letter off PATH instead of PATH
from RULE; `|` is not a legal Windows path character, so it cannot
collide with PATH.

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
| `group "G"` | `group=G` (one per entry, T-0272) |
| `sudoers "R"` | `sudoers=R` (one per entry, T-0272) |
| `platform "P"` | `platform=P` (T-0261) |
| `service_account "N" [gmsa]` | `service_account=N` (+ `service_account_gmsa` bare marker, T-0261) |
| `service` | `service` (T-0261) |
| `acl "P" "R"` | `acl=P\|R` (one per entry, T-0261 -- `\|`, not `:`, separates PATH from RULE; #hostacl-rule-validation above) |
| `pipe "N"` | `pipe=N` (one per entry, T-0261) |

## HostManifest

`src/frob/strata/_host.py::host_manifest_for(node)` reads a `Node`'s
attrs (of either origin, node- or store-derived) back into one typed
`HostManifest`:

```python
class HostManifest(BaseModel):
    platform: HostPlatform     # discriminator; LINUX_SYSTEMD or WINDOWS (T-0261)
    runs_as: str | None
    is_unit: bool
    owns: tuple[HostOwns, ...]  # HostOwns(path, mode)
    listens: tuple[int, ...]
    group: tuple[str, ...]      # T-0272
    sudoers: tuple[str, ...]    # T-0272
    service_account: str | None       # T-0261, windows analog of runs_as
    service_account_gmsa: bool        # T-0261
    is_service: bool                  # T-0261, windows analog of is_unit
    acl: tuple[HostAcl, ...]          # T-0261, HostAcl(path, rule); windows analog of owns
    pipes: tuple[str, ...]            # T-0261
```

Every field is read back regardless of which platform the node declared
-- `platform` is informational for a downstream consumer to branch on,
not a parser-level exclusivity fence (a windows node with `owns`/
`listens` populated, or a linux node with `acl`/`pipe` populated, both
still produce a manifest). This mirrors how `group`/`sudoers` were
already read regardless of any platform gating before T-0261 existed.

### MODE/PORT validation (T-0270, deferred from T-0255)

`strata-core/src/parse.rs`'s grammar keeps `owns`' MODE and `listens`'
PORT platform-agnostic atoms (a string, a number) -- the surface grammar
has no notion of "which OS". Validation instead fires at elaborate/
read-back time in `_host.py`, where the platform IS known
(`HostPlatform.LINUX_SYSTEMD` today):

- `HostOwns.mode` is validated (a pydantic `field_validator`) to be 3-4
  octal digits (`0-7`), matching `chmod`'s own shape -- `"0644"`/`"0755"`
  pass, `"999"` (out-of-range digits) and `"rwx"` (non-octal) are
  rejected. A 4-digit mode (`"4755"`) is how a setuid path is declared
  (#the-honest-gap above) and is accepted.
- `HostManifest.listens` is validated (a pydantic `field_validator`) to
  have every PORT in `1-65535`; a non-numeric PORT atom (`listens=abc`)
  is rejected with a plain `ValueError` before the range check ever
  runs.

Both fail closed: a malformed MODE or PORT raises (`pydantic.
ValidationError` for a bad MODE/out-of-range PORT, `ValueError` for a
non-numeric PORT) out of `host_manifest_for` rather than being silently
stored and trusted by a downstream consumer (T-0256/T-0257/T-0258/
T-0259). `mode` stays a bare `str` field (not a stricter octal-int
type) even after validation -- it is still platform-opaque by design, so
a future Windows ACL/SDDL string (T-0261) gets its own validator on the
SAME field, not a type change.

Returns `None` when the node declares no std.host construct at all --
distinguishing "no OS-layer facts" from "an OS-layer declared with
nothing set" (an empty-but-present manifest would be a different claim).

`platform` is the discriminator T-0261 fills in: `HostPlatform.WINDOWS` is
produced when a node/store declares an explicit `platform "windows"`
clause, `HostPlatform.LINUX_SYSTEMD` remains the default when no
`platform` clause is present at all (backward compatible with every
pre-T-0261 manifest). An explicit `platform` value other than `"windows"`
fails closed with a `ValueError` at `host_manifest_for` time. T-0256
(isolation proofs), T-0257 (generator), T-0258 (conformance checker), and
T-0259 (VM auditor) each still branch on `platform` per their own scope --
T-0261 ships the manifest + model only (same manifest-only scope T-0255
shipped for linux), NOT a windows-side movement-impossibility proof, deploy
generator, conformance checker, or VM auditor; wiring `HOST001`/`HOST002`
(and their `_scenarios.py` compromised-user builder) to also branch over
`HostAcl`/`service_account`/pipes is deliberately deferred to a follow-up
ticket, the same staged sequencing T-0256/T-0257/T-0258/T-0259 already
followed for linux. This is the "one manifest, no duplication" requirement
from T-0254's spec: every downstream ticket reads one parse of the attr
convention, not an independent re-parsing per platform.

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
  across users without a declared `Flow` bridging their nodes, and
  (T-0272) no shared OS group.
- **HOST002 (vertical movement)**, per service user: no setuid path
  owned, no sudoers grant (T-0272), no root-run unit whose owned
  paths this user can write to, and no write access to a path a
  higher-trust node also owns.

### Shared-group and sudoers sub-targets (T-0272)

`std.host`'s grammar originally had no OS-group or sudoers-grant
vocabulary (T-0256 was scoped to `src/frob/strata/**`, not
`strata-core/**`, so it could not add either), so the `shared-group` and
`sudoers` sub-targets UNCONDITIONALLY fired until an operator wrote an
explicit `waive "HOST001:shared-group" reason="..."` /
`waive "HOST002:sudoers" reason="..."` clause. T-0272 added `group
"NAME"`+ and `sudoers "RULE"`+ to the grammar (#surface-grammar above),
so both sub-targets now derive REAL findings from `HostManifest.group`/
`HostManifest.sudoers` intersection, the same DERIVED-not-hand-written
discipline every other sub-target follows: `shared-group` fires once per
OS group two users' `group` tuples have in common; `sudoers` fires once
per grant a user's `sudoers` tuple declares. A pair/user with no
declared `group`/`sudoers` now correctly produces no finding.

<!-- frob:invariant INV-033 -->

`setuid`
needed no new grammar at all -- a 4-digit `owns "PATH" "4755"` mode
already carries the setuid bit.

### Windows wiring (T-0606)

T-0261 shipped the Windows `std.host` surface (#windows-surface-grammar
above) but explicitly deferred wiring it into HOST001/HOST002 -- until
T-0606, a windows-only node declaring solely `service_account`/`acl`/
`pipe` produced NO HOST001/HOST002 findings at all, not because it was
proven isolated but because nothing read its windows-shaped facts
(#scope-boundary-what-is-not-built-here below, pre-T-0606 wording).
T-0606 generalizes every identity/path/listening-surface join
`_host_isolation.py` performs to read EITHER platform's fields, without
ever branching the rule logic itself on `HostManifest.platform`:

- **Service-user identity**: a manifest's `runs_as` (linux) or
  `service_account` (windows) -- whichever is set -- is the one identity
  `HOST001`/`HOST002`/`build_compromised_user_scenario` group nodes by.
- **Owned paths**: linux `owns` (POSIX MODE) and windows `acl` (NTFS
  DACL RULE) are merged into one per-user path index; a path's
  write-capability reads the POSIX owner-write bit for an `owns` entry
  or "RIGHTS is `Write`/`Modify`/`FullControl` and not `:deny`'d" for an
  `acl` entry. `shared-writable-path`, `root-unit-writable-by-user`, and
  `write-to-higher-trust-path` all read this merged index, so a
  linux/windows or windows/windows pair proves the identical shape of
  finding a linux/linux pair does. `setuid` stays linux-only by
  construction (no NTFS ACL bit maps onto POSIX setuid) -- an honest
  absence, not a fabricated windows equivalent.
- **Listening surface**: linux `listens` (PORT) and windows `pipe` (named
  pipe) are merged into one labeled set per user, so `cross-user-socket`
  fires on a shared PORT, a shared PIPE, or one of each. `host_movement_
  flows` mirrors the same union so `build_compromised_user_scenario`'s
  blast-radius claims stay non-vacuous over a shared windows pipe exactly
  like they already were over a shared linux port (#movement-
  impossibility-proofs above, T-0256's REJECT-round fix).
- **Root-run identity**: a linux `unit` with no `runs_as` OR a windows
  `service` with no `service_account` (SCM's own LocalSystem default) is
  the root-run-equivalent identity `root-unit-writable-by-user` guards
  against.

`group`/`sudoers` (T-0272, above) needed no change: neither field was
ever platform-gated, so a windows node declaring them already derived
real findings before T-0606.

### Multi-ACE deny-overrides-allow join, and the WRITE_DAC indirection corner (T-0792/T-0825)

`_join_acl_entries` joins EVERY `acl` ACE declared for a path (across all
of a user's nodes), grouped by PRINCIPAL: an explicit `:deny` ACE always
wins over an explicit allow ACE for the SAME principal regardless of
declaration order (real NTFS deny-overrides-allow evaluation), and a deny
for one principal never reaches across to cancel a DIFFERENT principal's
allow (T-0792, replacing a last-declaration-wins collapse that could
silently drop an unrelated principal's real grant).

`_ACL_WRITE_RIGHTS` (`write`/`modify`/`fullcontrol`) is a coarse, single-
token vocabulary -- real NTFS RIGHTS are bit-sets that nest (`write` bits
subset `modify` bits subset `fullcontrol` bits), and ONLY `fullcontrol`
additionally carries WRITE_DAC/WRITE_OWNER, bits neither `write` nor
`modify` grant at any level. T-0792's reviewer flagged the one corner this
coarseness understates (T-0825 closes it): a same-principal narrow deny
(`Modify`) alongside a broad allow (`FullControl`) nets to "not
write-capable" in the naive per-principal join, but real NTFS still grants
WRITE_DAC/WRITE_OWNER through the `FullControl` allow -- the `Modify` deny
never reaches those bits -- so the "denied" principal can rewrite the
path's own DACL and grant themselves full write back. `_join_acl_entries`
(T-0825) resolves this by ranking each principal's net allow/deny by
level (`_RIGHTS_RANK`): when the net allow is `fullcontrol` and the net
deny is anything NARROWER than `fullcontrol`, the join still returns
write-capable for that principal (the indirection survives) -- only an
explicit `fullcontrol`-level deny (which does reach WRITE_DAC/WRITE_OWNER
too) counts as a genuinely clean deny. A narrower allow (`write`/
`modify`) never grants WRITE_DAC in the first place, so any same-or-lower
level deny against it still fully cancels it, unchanged from before this
fix. `tests/unit/strata/test_host_isolation.py::
TestMultiAceDenyOverridesAllow` locks both the indirection corner (now
`True`) and its `fullcontrol`-deny/`fullcontrol`-allow counter-case (still
`False`).

The privilege-clause gap named alongside this in the T-0792 module
docstring (SeImpersonate/SeDebug-class windows token privileges needing
their own `strata-core` grammar clause, distinct from `owns`/`acl`'s
path-permission vocabulary) remains open -- no such grammar exists yet,
disclosed here rather than silently dropped; filing that as its own
grammar-extension ticket is future work, not folded into this fix.

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
- No OS-group / sudoers grammar gap remains -- T-0272 closed
  T-draft-7b5b5541 (filed by T-0256); see #shared-group-and-sudoers-sub-
  targets-t-0272 above.
- T-0261 ships `HostPlatform.WINDOWS` + the five Windows clauses
  (#windows-surface-grammar above): manifest + model only, mirroring
  T-0255's own manifest-only scope for linux. STILL NOT built here: a
  windows-side deploy generator (no `frob deploy generate` output for SCM
  services/gMSA provisioning/ACL application), a windows-side conformance
  checker, a windows VM auditor. T-0606 CLOSED the movement-impossibility
  half of this gap: `HOST001`/`HOST002`/`_scenarios.py::
  build_compromised_user_scenario` now branch on `service_account`/`acl`/
  `pipes` too (#windows-wiring-t-0606 below) -- a windows-only node
  declaring solely `service_account`/`acl`/`pipe` (no `runs_as`/`owns`/
  `listens`/`group`/`sudoers`) now produces the SAME shape of HOST001/
  HOST002 findings a linux node would, equivalent in strength to the
  linux path. The deploy-generator/conformance/VM-auditor gaps above
  remain open, unaffected by T-0606's scope.

## Resource contention (SYS2xx, T-0699)

`_contention.py::check_resource_contention` reads the SAME `HostManifest`
(plus `KernelModel.flows`) this page documents to find four kinds of
cross-node resource contention, no grammar change:

- **SYS200 duplicate port** -- two distinct nodes both declare the same
  `listens` PORT. Always a hard conflict.
- **SYS201 overlapping path claim** -- two distinct nodes' `owns`
  (linux) or `acl` (windows) PATH atoms overlap by directory-segment
  prefix. `write_capable` is set when either side's claim grants
  write-capable rights (a POSIX `owns` MODE with a write bit set, or a
  non-`:deny`'d `acl` RULE whose RIGHTS is `Write`/`Modify`/
  `FullControl`).
- **SYS202 shared pipe** -- two distinct nodes bind the same `pipe`
  NAME.
- **SYS203 shared store write** -- two or more distinct nodes have a
  `Flow` edge landing on the same store node.

MODE-BLIND, HONESTLY: `Flow` carries no read/write direction today, so
SYS203 counts ANY inbound flow to a store as a "write" -- deliberately
coarser than a real read/write distinction. This is the grammar-data
ceiling this ticket ships against; a flow-level read/write mode (and a
MODE-aware SYS201 severity) is T-0700's sibling grammar-extension ticket
(below), not duplicated here -- T-0700 upgrades the model with a mode-
AWARE proof (SYS204) alongside SYS200-203 rather than renaming or
replacing them. `store_ids` (which node ids are STORES) is not
reconstructible from `KernelModel` alone -- a store desugars into a plain
`Node` at elaborate time with no surviving marker -- so a caller must pass
in `Module.stores`' ids explicitly; an empty `store_ids` (the default)
makes SYS203 silent rather than guessing.

All four rules join the SAME T-0174 waiver channel SYS100-102 use
(`_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES`, `RULE:SUBTARGET` required
-- the sub-target is the port number, the overlapping path, the pipe
name, or the store id).

### SYS203 arbiter-awareness (T-1025)

SYS203 used to be permanently arbiter-blind on top of being mode-blind: it
had no code path that consulted `Module.resources` (the
`resource ID { arbitrated_by NODE | lock "NAME" }` declaration below) at
all, so a store with a genuinely-modeled, provably-safe arbiter still
fired SYS203 on every writer, forever, with no way to discharge it short
of a standing waiver. `check_resource_contention` (and
`_shared_store_write_violations`) now accept an optional `module: Module
| None` parameter -- when a store id is ALSO a `resource` id declaring
`arbitrated_by`/`lock`, its SYS203 finding is skipped entirely (not
merely waived), the same discharge condition SYS204's
`resource_contention_violations` already applies (below). `module=None`
(the default) keeps every pre-T-1025 caller's behavior byte-for-byte
unchanged -- purely additive, no signature break.

**Disclosed gap, not silently left incomplete:** the LIVE `SELFAUDIT001`
gate (`frob check --only sys`, `src/frob/gates/__init__.py`) and the
`frob sys audit` CLI report (`src/frob/app/sys_runner.py`) both call
`check_resource_contention` today WITHOUT a `module=` argument -- neither
of those files, nor `_design_load.py`'s `DesignIds` (which has no
`Module`-carrying field to source one from), is in this ticket's declared
`scope`. Wiring `module` through those callers is real, disclosed
follow-up work (see this ticket's Done report for the filed id), not done
here -- the five `SYS203:tickets_ledger` waivers in `design/frob.strata`
therefore stay in place for now: dropping them without that wiring would
regress the live gate from clean to five errors, verified directly (the
same `check_resource_contention(model, store_ids=...)` call the live gate
makes, with no `module`, still reports all five findings against the
current `design/frob.strata`). The capability itself is fully built and
tested (`tests/unit/strata/test_contention.py::TestSharedStoreWrite`,
including `contention_store_arbitered.strata`'s dedicated litmus fixture)
-- only the last-mile CLI wiring remains.

### SYS201 arbiter-awareness (T-1149)

SYS201 had the exact same blind spot SYS203 used to before T-1025: two
nodes legitimately sharing one arbitered resource (e.g. tickets_ledger's
five writers, all serialized through the SAME `.frob/tickets.lock`
flock) would fire a FALSE overlapping-path conflict the moment either
declared an `owns`/`acl` path claim scoping its access -- discovered when
T-1061 wired SYS205's WRITE mode path-scoping live and a synthetic
`owns="tickets.md"` declaration (tried to discharge SYS205) was measured
to create 20 new SYS201 findings across the five writers.
`_overlapping_path_violations` now also accepts the SAME `module: Module
| None` parameter SYS203 already takes (threaded through
`check_resource_contention`, `_arbitered_access_by_node`): if the two
nodes in an overlapping-path pair both declare `access "RESOURCE" mode
MODE` (below) to a COMMON resource id that itself declares an arbiter,
the pair is skipped entirely -- the model already proves those two nodes
coordinate through that arbiter, so the raw path overlap is no longer an
undeclared conflict. `module=None` keeps every pre-T-1149 caller's
behavior byte-for-byte unchanged.

**Same disclosed gap as SYS203/T-1025, not re-derived:** the LIVE
`SELFAUDIT001` gate and `frob sys audit` CLI still call
`check_resource_contention` without a `module=` argument (T-1025's
"Disclosed gap" paragraph above explains exactly why -- neither caller,
nor `DesignIds`, is in this ticket's declared `scope` either). The five
`SYS205:tickets_ledger` waivers in `design/frob.strata` therefore also
stay in place: SYS201 gaining the CAPABILITY to discharge a common-
arbiter pair does not by itself let anyone actually drop a synthetic
`owns=` declaration and lean on it live, until that same `module=`
wiring lands for both SYS203 and SYS201 together. The capability itself
is fully built and tested
(`tests/unit/strata/test_contention.py::TestOverlappingPath`, including
`contention_path_arbitered.strata`'s dedicated litmus fixture) -- only
the last-mile CLI wiring remains, same as SYS203's own disclosed cut.

## Resource access modes (T-0700)

`_access.py` adds a MODE-aware contention proof (SYS204) alongside
SYS200-203 above, using a NEW grammar surface rather than retrofitting
`owns`/`acl`/`listens`/`pipe`'s existing shapes:

- **`access "RESOURCE" mode MODE`** -- a node/store clause (repeatable,
  T-0261 node/store symmetry) naming a shared resource by an opaque
  STRING id and its declared access mode: `read`, `append`, `alpha`,
  `write`, or `exclusive`. Desugars straight to an `access=<resource>:
  <mode>` attr (`strata-core/src/parse.rs::parse_access_attr`, the
  `bin_path` T-0629 direct-attr-push shape -- no new `NodeDecl`/
  `StoreDecl` field), read back by `_access.py::node_access_declarations`.
- **`resource ID { arbitrated_by NODE | lock "NAME" }`** -- a top-level
  statement naming a shared resource and, optionally, its single arbiter
  (a node id) or lease/lock name. At most one of the two may be given (a
  parse error otherwise). A resource has no accessor of its own, so
  unlike `access` it cannot desugar into an attr -- it lands on
  `Module.resources` (`_ast.py::ResourceDecl`) instead.

**Compatibility matrix** (`_access.py::mode_conflict`, user-specified
2026-07-22 semantics): `alpha` declares INTEREST in a future writer lock
-- many writes need a read just before, so `alpha` sits between `read`
and `write`. Only two pairings are safe:

| | read | alpha | write/append/exclusive |
|---|---|---|---|
| **read** | OK | OK | CONFLICT |
| **alpha** | OK | CONFLICT | CONFLICT |
| **write/append/exclusive** | CONFLICT | CONFLICT | CONFLICT |

`alpha+alpha` conflicts (exactly one writer-intender per resource --
this is what prevents the two-readers-both-upgrading deadlock); an alpha
holder upgrades to write only once readers drain. `append`/`exclusive`
are folded in as write-like (a documented judgment call, module
docstring) -- `exclusive` is, if anything, stricter than plain `write`
(conflicts even with another `exclusive`, or a lone `read`).

**SYS204 unarbitrated mode conflict** (`_access.py::
resource_contention_violations`): for every resource id at least one
`access` clause references, every conflicting PAIR of accessors fires
fail-closed UNLESS the resource declares an arbiter (`arbitrated_by` or
`lock`) -- a declared arbiter is trusted to make the pair provably safe at
the MODEL level; whether the arbiter is actually RESPECTED by the node's
code is T-0701's separate, code-level conformance proof, not this
check's job. A resource with only ever ONE declared accessor, or whose
accessors are all `read`/`read`+`alpha`, never fires -- no pairwise
conflict exists to find.

Field motivation: frob's own ledger-lock/refs-stash/`.git/info/exclude`
incidents (docs/guides/agent-playbook.md sections 1b/1c) -- repo-global
resources with multiple writers and only convention, not a declared
arbiter, keeping them safe.

DELIBERATELY NOT WIRED IN THIS PASS (disclosed cut, `_access.py` module
docstring): CLI dispatch (`frob sys audit`, `src/frob/app/sys_runner.py`)
and the T-0174 `MULTI_INSTANCE_WAIVER_FAMILIES` waiver channel are both
shared surfaces a concurrent sibling ticket's obligation batch may be
touching -- `resource_contention_violations` is a pure, fully-tested
function; wiring it into the CLI/waiver channel is a follow-up ticket.

### SYS205 mode conformance (T-0701, v1 T-1060)

`_mode_conformance.py::check_mode_conformance` proves the CODE-level
half SYS204 defers: a node's OWN bound python code must actually behave
the way its declared `access ... mode MODE` clause claims (the
catalogued-is-not-enforced trap, T-0343 doctrine). A v0 textual join
(T-0701) scans a node's bound `.py` files for a small curated set of
write-capable operation shapes and checks them against each declared
mode's semantics (READ: zero write-capable ops anywhere; APPEND: only
`open(path, "a"...)`-shaped opens; ALPHA/EXCLUSIVE: every write-capable
op must sit inside a `with <lock>:` block naming the resource's declared
`lock`; WRITE: unrestricted). T-0701 disclosed three v0 cuts; T-1060
closes all three, each as a narrow textual approximation (deliberately
NOT tree-sitter-based like `frob.arch._lock_ordering`'s own T-0694 lock-
identity mechanism -- a heavier, differently-scoped tool this ticket does
not adopt):

1. **ALPHA/EXCLUSIVE upgrade-deadlock anti-pattern** -- a write-capable
   op nested inside TWO `with <lock>:` blocks naming the SAME lock (a
   non-reentrant lock reacquired by the same holder) now fires a NEW
   `alpha_reacquire_deadlock` category, alongside (not instead of) the
   existing unguarded-write check -- the write IS lexically inside a
   block naming the lock (so the old check alone would call it
   conformant), but the reacquisition itself is the specific deadlock
   shape `alpha`/`exclusive` exist to prevent. Telling two DIFFERENT
   lock OBJECTS with the same NAME apart (T-0694's harder lock-identity
   problem) is still out of scope -- this only catches literal name
   reuse.
2. **`arbitrated_by NODE` code-identity** -- a resource's arbiter is no
   longer required to be a `lock`: an `arbitrated_by NODE` arbiter is
   now code-checkable too, via a cheap textual convention (the write-
   capable line must mention the arbiter node's id as a dotted-call
   prefix, `"{node_id}."`) rather than real cross-node call-graph
   resolution -- a write routed through the arbiter via an alias,
   returned callable, or injected dependency is still invisible to this
   join and fails closed as unguarded. A resource declaring NEITHER
   `lock` nor `arbitrated_by` still fails closed exactly as before.
3. **WRITE path-scoping** -- WRITE is no longer unconditionally
   unrestricted: it now reuses the SAME per-node `owns`/`acl` "declared
   path" fact SYS201 (`_contention.py`) already reads off
   `_host.py::host_manifest_for`. A node declaring NO `owns`/`acl` at
   all now fails closed (`no_declared_path`) -- the same "nothing
   code-checkable was declared" posture ALPHA/EXCLUSIVE's `no_arbiter`
   category already establishes. When paths ARE declared, a
   write-capable line whose call shape carries a literal string path
   argument (`open()`/`os.remove`/`os.rename`/`os.unlink`/
   `shutil.rmtree`/`shutil.move` -- the shapes with an explicit PATH
   argument; `.write_text(`/`.write_bytes(`/`.unlink(`/`.send(`/SQL DML
   have none) is checked for directory-segment-prefix overlap against
   the declared paths; no overlap fires `write_outside_declared_path`.
   A write with no extractable literal (a dynamic path, or a category
   with no path argument at all) cannot be judged by this v1 pass and
   stays silent -- disclosed, not a false pass: real path-literal
   resolution (constant-folding, f-strings) is the same class of "needs
   real static analysis" cut the other two v1 joins above accept.

#### CLI dispatch + waiver channel (T-1061)

`check_mode_conformance` was a pure, fully-tested function with no
production caller until T-1061 -- the same disclosed cut `_access.py`'s
own SYS204 module docstring names for CLI dispatch and the waiver
channel. T-1061 closes it on both fronts:

- **`frob sys audit`** (`src/frob/app/sys_runner.py::_run_audit`) now
  runs SYS205 alongside SYS100-103/SYS2xx/REL2xx and prints a
  `_print_mode_conformance_report` summary (PROVED/GAP lines matching
  the other families' CI-parseable style, waived count carried inline
  same as `_print_contention_report`); a SYS205 finding makes the whole
  audit exit nonzero, same as any other family.
- **`frob check`'s SELFAUDIT001 gate**
  (`src/frob/gates/__init__.py::_selfaudit_violations`) now folds SYS205
  findings into the SAME wrapped `Violation` stream SYS100-103/SYS2xx/
  REL2xx already use -- suppressible the ordinary GATES-layer way too
  (`frob:waive SELFAUDIT001:<node> reason="..."`), same as any other
  SELFAUDIT001-wrapped finding.
- **`.strata`-level `waive "SYS205:<resource>"`** (the actual "waiver
  channel" T-1061's title names): `check_mode_conformance` gained a REAL
  internal waiver-application pass, `_apply_mode_conformance_waivers`,
  mirroring `_contention.py::_apply_contention_waivers`'s exact pattern
  -- `ModeConformanceReport` now carries both `violations` (unwaived) and
  `waived` (T-0174: suppressed, never silently dropped). `SYS205` joined
  `_waive.py::MULTI_INSTANCE_WAIVER_FAMILIES` (it can fire more than once
  per node, once per resource, `ModeConformanceViolation.resource`
  already tracks which), so a `waive` clause naming it MUST carry a
  `RULE:SUBTARGET` sub-target (`waive "SYS205:tickets_ledger" ...`), same
  discipline SYS100/SYS101/SYS200-203 already established. This piece
  was NOT originally planned in T-1061's declared scope
  (`_mode_conformance.py`/`_waive.py` were added mid-ticket) -- wiring
  SYS205 live against frob's OWN design/frob.strata surfaced a genuinely
  new SYS205 finding on the five `tickets_ledger` write-mode accessors
  (no `owns`/`acl` path declared for any of them), and the only clean
  discharge path that did not ALSO regress SYS201 (declaring a synthetic
  `owns="tickets.md"` on all five creates 20 new overlapping-path
  findings, verified directly -- SYS201 has no arbiter-awareness, unlike
  SYS203/T-1025) was giving SYS205 a real waiver channel and waiving
  those five findings by name, with an honest reason recorded in
  `design/frob.strata` itself.

Both callers need a `Module` carrying `.resources` (the `lock`/
`arbitrated_by` arbiter lookup ALPHA/EXCLUSIVE's T-1060 widening reads)
that `DesignIds` did not previously expose -- `_design_load.py::
DesignIds` gained a new `resources: tuple[ResourceDecl, ...]` field
(T-1061, collected the SAME way `store_ids` already is: off each file's
PARSED, pre-elaboration `Module.resources`, before `elaborate` drops
that field entirely). Both `sys_runner.py` and `gates/__init__.py`
build a throwaway `Module(name=..., resources=ids.resources)` to pass
in, since `.resources` is the only field either check reads off a
`Module` argument.

## See also

- `docs/commands/deploy.md` -- `frob deploy generate`, DEPLOY001, and the
  T-0257 scope/honesty notes.
- `src/frob/strata/_contention.py` -- `check_resource_contention`,
  `ResourceContentionViolation`, `ResourceContentionReport`, SYS200-203.
- `tests/unit/strata/test_contention.py` -- the SYS200-203 firing/clean
  litmus pairs (T-0699).
- `docs/strata/surface.md#node-grammar-implemented-t-0132-closes-the-codemay-gap` -- the node/store grammar this
  vocabulary extends.
- `docs/strata/surface.md#key-construct-semantics` -- "a store is a node
  too", the precedent every store-side clause here follows.
- `src/frob/strata/_host.py` -- `host_attrs`, `host_manifest_for`,
  `HostManifest`, `HostOwns`, `HostAcl` (T-0261), `HostPlatform`.
- `src/frob/strata/_host_isolation.py` -- HOST001/HOST002,
  `HostIsolationViolation`, `evaluate_host_isolation_waived`,
  `COMPROMISED_OWNER_CATALOG`. Windows-aware since T-0606
  (#windows-wiring-t-0606 above).
- `src/frob/strata/_scenarios.py::build_compromised_user_scenario` --
  the compromised-owner red-team scenario builder.
- `tests/unit/strata/test_litmus_host.py` -- parse -> elaborate ->
  `host_manifest_for` round trip over the declared/undeclared litmus
  pair (linux/systemd) and the windows-declared litmus fixture (T-0261).
- `tests/unit/strata/test_litmus_host_isolation.py` -- the shared-user
  VULN / isolated HARDENED litmus pair for HOST001/HOST002.
