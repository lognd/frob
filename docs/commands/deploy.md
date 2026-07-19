# frob deploy

Compiles `std.host` (T-0255) `HostManifest` facts into Linux/systemd
install/status/uninstall bash (T-0257, deploy epic T-0254). One verb
today: `generate`.

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

## Scope and honesty notes

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
- `src/frob/app/deploy_runner.py` -- the `frob deploy generate` CLI
  entry point.
