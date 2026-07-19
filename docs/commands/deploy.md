# frob deploy

Compiles `std.host` (T-0255) `HostManifest` facts into Linux/systemd
install/status/uninstall bash (T-0257, deploy epic T-0254), and
empirically proves the result is artifact-free via a VirtualBox
snapshot-diff harness (`audit`, T-0259). Two verbs: `generate` and
`audit`.

## Quickstart

```bash
frob deploy generate                # write deploy/install.sh, status.sh, uninstall.sh
frob deploy generate --check        # verify committed scripts match the current model; no writes
frob deploy generate /path/to/repo  # generate for a different repo root
```

Same repo-root convention as `frob sys` (`docs/commands/sys.md`
"Quickstart"): `<path>` (default `.`) is the repo root, and the command
appends the configured design dir itself (default `design/`, or
`[strata].design_dir` in `frob.toml`).

## What gets generated

Every node/store declaring a `std.host` construct (`docs/strata/host.md`)
produces one entry in each of three scripts, written to `deploy/` (or
`--out-dir`):

- **`install.sh`** -- check-then-apply per step, so a re-run performs
  zero commands and exits 0 (idempotent by construction, not merely by
  intent): creates the declared service user (`runs_as`) if it does not
  already exist; writes a hardened `systemd` unit
  (`NoNewPrivileges=yes`, `ProtectSystem=strict`, `PrivateTmp=yes`,
  `CapabilityBoundingSet=` derived from `may` capabilities,
  `SystemCallFilter=` reusing the EXISTING seccomp exporter
  `frob.strata.node_allowed_syscalls` -- one join, not a second one) and
  enables+starts it only if its content hash actually changed; sets
  exact ownership/mode on every `owns` entry, comparing current vs.
  declared state before touching anything.
- **`status.sh`** -- per unit, `systemctl is-active`/`is-enabled` plus a
  `/dev/tcp` probe of every declared `listens` port, one
  machine-parseable `key=value ...` line per fact.
- **`uninstall.sh`** -- removes EXACTLY the manifest's own set: units
  stopped+disabled+deleted, owned paths deleted, service users removed
  -- nothing else. Artifact-freeness (nothing outside the manifest
  survives an uninstall) is manifest COMPLETENESS, which T-0254 child
  5's VM audit proves empirically.

## DEPLOY001: the drift lock

Every generated script's header carries a
`# frob-deploy-manifest-digest: <sha256>` line. Once a `deploy/`
directory exists in the repo, `frob check` runs an opt-in DEPLOY001
check (`frob.deploy.deploy_drift_violations`, wired into
`frob.app.check_runner` as an extra `deploy-drift` stage -- NOT part of
`frob.gates`'s pluggable job table, since `src/frob/gates/**` was out of
T-0257's declared scope) that recompiles the three scripts from the
CURRENT design model and compares full body text against what is
committed. A mismatch -- a hand-edit, or a design change nobody
regenerated for -- fails `frob check` with the exact filename named.
`frob deploy generate --check` runs the identical comparison standalone
(useful for a pre-commit hook without pulling in the rest of `frob
check`).

## DEPLOY002/DEPLOY003: bidirectional conformance

`frob.deploy.deploy_conformance_violations` (wired into `frob check` as
an extra `deploy-conformance` stage, same non-`frob.gates` shape
DEPLOY001 uses) parses each committed `deploy/install.sh`/`uninstall.sh`
into its actual MUTATION SURFACE (structured `useradd`/`groupadd`/
`userdel`/`groupdel`/`mkdir`/`install`/`cp`/`chown`/`chmod`/`rm -f`/
`rm -rf`/`systemctl enable|disable|start|stop`/unit-heredoc extraction,
anchored to `_generate.py`'s exact check-then-apply command shapes) and
compares it BIDIRECTIONALLY against the current model's `HostManifest`
set:

- **DEPLOY002** -- the script mutates something the manifest does not
  declare (a smuggled extra user/path/unit). Fires even if DEPLOY001's
  digest still matches, so hand-appending one rogue command after a
  clean regeneration does not slip past `frob check`.
- **DEPLOY003** -- the manifest declares something no script mutation
  implements (an incomplete install or uninstall).

Full design narrative: `docs/strata/host.md#deploy002deploy003-
conformance`.

## `frob deploy audit --vm`: the VM snapshot-diff harness

DEPLOY001/DEPLOY002/DEPLOY003 above prove the SCRIPTS are internally
consistent (regeneration-stable, mutation-surface-exact against the
model) -- entirely statically, no VM required. `frob deploy audit --vm
<name>` (T-0259, deploy epic T-0254 child 5) proves the scripts, RUN
against a real host, actually leave the host exactly as declared. It is
expensive (needs a real VirtualBox guest) and deliberately NOT part of
`frob check`/`make check` -- run it via `make deploy-audit` or `frob
deploy audit` directly, typically before a release or when
`install.sh`/`uninstall.sh` themselves change.

```bash
frob deploy audit --vm my-vm \
    --ssh-host 10.0.2.15 --ssh-user root --ssh-key ~/.ssh/frob_vm_key \
    --base-snapshot base --output deploy-audit-attestation.json

# or, with env vars:
FROB_VM=my-vm FROB_VM_SSH_HOST=10.0.2.15 FROB_VM_SSH_KEY=~/.ssh/frob_vm_key \
    make deploy-audit
```

### The sequence (state CHECK at every checkpoint)

Per the ticket's user-specified spec, a CHECK is always BOTH halves
together -- a state capture AND a `status.sh` health assertion -- never
capture alone, so a broken install is caught at the checkpoint it broke,
not several steps later when a diff comes up unexpectedly non-empty:

```
restore base snapshot
  -> CHECK C0  (capture S0; assert status.sh reports NOT-installed)
  -> install.sh
  -> CHECK C1  (capture S1; assert status.sh reports healthy)
  -> install.sh AGAIN
  -> CHECK C1' (capture S1'; assert status.sh reports healthy)
  -> uninstall.sh
  -> CHECK C2  (capture S2; assert status.sh reports NOT-installed)
```

### State capture

Each capture (`frob.deploy.StateCapture`) records: a filesystem manifest
(sha256 hash, owner, group, mode) over every path the manifest's `owns`
entries + generated unit files declare; the full text of `/etc/passwd`
and `/etc/group`; every generated systemd unit file's body plus the
enabled-unit set; and the listening-socket set (`ss -tln`). Capture is
ssh-driven (`frob.deploy._vm_runner._capture_state`) -- see "Scope and
honesty notes" below for the one honest scope cut in what gets hashed.

### VM orchestration

`frob.deploy._vm_runner` drives the sequence above against a real
guest: power off + `VBoxManage snapshot restore` + `startvm --headless`
for the base-snapshot restore, `scp` to stage the three generated
scripts, and `ssh` for every command run on the guest (`status.sh` at
each CHECK, `install.sh`/`uninstall.sh`, and the state-capture reads).
`run_vm_audit` checks `vboxmanage_available()` FIRST, before any other
subprocess call -- see "Testing posture" below for why this file is kept
this thin.

### The four proofs

- **idempotence**: `diff(S1, S1')` is EMPTY -- installing twice performs
  zero mutations the second time.
- **artifact-freeness**: `diff(S0, S2)` is EMPTY -- install then
  uninstall leaves the host exactly as it started.
- **install-exactness**: the set of paths/units/users `diff(S0, S1)`
  touches equals `frob.deploy.expected_mutation_surface(entries)`
  (T-0258) EXACTLY -- nothing extra (a smuggled mutation), nothing
  missing (an incomplete install).
- the four status assertions themselves (C0/C1/C1'/C2 above) -- checked
  via `frob.deploy.assert_not_installed`/`assert_healthy`.

### Status assertions

`assert_not_installed(status_text)` (C0/C2): every unit line in
`status.sh`'s output must report `inactive`/`disabled` (or be absent
entirely, the pre-first-install case). `assert_healthy(status_text,
expected_units)` (C1/C1'): every expected unit must appear with
`active=active enabled=enabled` -- a unit missing from the output
entirely (a silently-failed install) fails this just as loudly as one
reporting `inactive`.

### Allowlist

All diffs are filtered through an allowlist first:

| pattern | why it's excluded |
| --- | --- |
| `/var/log/**` | normal log growth from the OS and from running the scripts themselves |
| `/etc/machine-id`, `/var/lib/dbus/machine-id` | D-Bus/systemd machine identity, can regenerate independent of this tool |
| `/run/**`, `/proc/**`, `/sys/**` | kernel-backed, never persisted, never declared by a `HostManifest` |
| `/tmp/**`, `/var/tmp/**` | ephemeral by design |
| `/var/lib/systemd/**` | systemd's own bookkeeping, touched by any `daemon-reload` |

### Attestation

`frob deploy audit` writes an `AuditAttestation` (`frob.deploy._audit`)
as JSON to `--output` (default `deploy-audit-attestation.json`):
timestamps, snapshot id, per-checkpoint status assertion results, and
all three proof results (plus the exact extra/missing target sets on an
install-exactness failure). Exit codes: `0` all proofs held, `1` ran but
at least one proof or status assertion failed, `2` `VBoxManage` not on
`PATH` -- SKIPPED, never a fabricated pass. Record a passing run as
ticket evidence via `frob ticket done --evidence-cmd 'frob deploy audit
--vm ...'` (T-0215) -- referenced as L4-class evidence for the
movement-impossibility claims (T-0256/T-0082 evidence-ladder precedent).

### Testing posture

`frob.deploy._audit` (diff/proof/attestation logic) is pure data-in,
data-out and fully covered by fixture-based unit tests
(`tests/unit/deploy/test_audit.py`) with no VirtualBox, no ssh, no VM
anywhere in that suite. `frob.deploy._vm_runner` is deliberately kept
thin (a sequence of `VBoxManage`/`ssh` subprocess calls) so the actual
VM orchestration -- restoring a snapshot, ssh'ing into a guest -- is the
ONLY untested-in-CI sliver of this feature;
`tests/unit/deploy/test_vm_runner.py` covers its one VM-free surface,
the graceful-degrade gate.

### Scope and honesty notes (audit)

- State capture hashes only the manifest-declared `owns` paths and
  generated unit files, not a full-disk walk (impractical over ssh for
  every audit run). A mutation entirely OUTSIDE both the manifest's
  declared paths and whatever `expected_paths` the caller derives is
  outside this capture strategy's reach -- a documented, honest scope
  cut, not a silent gap: DEPLOY002/DEPLOY003 (static) plus install-
  exactness (empirical, over the declared surface) are the two lines of
  defense against a smuggled mutation; a third one entirely off the
  design model's radar is a manifest-completeness problem the static
  gates cannot see either.
- ssh/sudo access to the guest is assumed pre-provisioned (module
  docstring); provisioning the guest itself (base image, ssh key
  injection, sudo NOPASSWD for the audit user) is out of this ticket's
  scope.

## Scope and honesty notes (generate)

- Builds on `HostManifest`/`host_manifest_for` (T-0255,
  `docs/strata/host.md#hostmanifest`) and coexists with the HOST001/
  HOST002 isolation checks (T-0256, `docs/strata/host.md#movement-
  impossibility-proofs`) -- neither is redefined here.
- Linux/systemd only. Windows (PowerShell) generation is a separate
  future ticket (T-0264), not built here.
- OS users do not yet join the trust lattice through any dedicated
  plumbing (T-0255's honesty note, inherited as-is): `runs_as` is read
  as a plain `HostManifest` field like any other field, never
  model-checked by the generator.
- `CapabilityBoundingSet=`/`SystemCallFilter=` are coarse, `may`-KIND-
  level mappings (`frob.deploy._generate._CAP_KIND_MAP`,
  `frob.strata._export._SECCOMP_KIND_MAP`) -- a capability KIND names a
  class, not an exact Linux capability or syscall list, until the
  surface grammar can express finer atoms (same deferral
  `docs/strata/host.md` and `_export.py`'s own docstring already note).

## See also

- `docs/strata/host.md#the-deploy-generator` -- the generator's design
  narrative, linked from the `std.host` doc itself.
- `src/frob/deploy/_generate.py` -- `generate_all`,
  `generate_install_script`, `generate_status_script`,
  `generate_uninstall_script`, `manifest_digest`.
- `src/frob/deploy/_drift.py` -- `deploy_drift_violations` (DEPLOY001).
- `src/frob/deploy/_conform.py` -- `deploy_conformance_violations`
  (DEPLOY002/DEPLOY003).
- `src/frob/app/deploy_runner.py` -- the `frob deploy generate`/`frob
  deploy audit` CLI entry points.
- `src/frob/deploy/_audit.py` -- `StateCapture`/`diff_states`/
  `idempotence_holds`/`artifact_freeness_holds`/
  `install_exactness_holds`/`assert_not_installed`/`assert_healthy`/
  `build_attestation` (T-0259, pure and fully unit-tested).
- `src/frob/deploy/_vm_runner.py` -- `run_vm_audit`/
  `vboxmanage_available` (T-0259, the VM-orchestration sliver).
