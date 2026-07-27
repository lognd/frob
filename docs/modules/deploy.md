# frob.deploy: windows generation (T-0264)

<!-- frob:ticket T-0264 -->
<!-- frob:waive INV003 reason="T-1023 INV003/INV004 burn-down: this file's 'only'/'never'/'requires' hits are incidental scope-cut/design-rationale prose (this page vs docs/strata/host.md's split, a comment about krb_manifest_for reuse, a code-sample docstring) rather than a genuine cross-module contract needing its own tracked invariant" -->
<!-- frob:waive INV004 reason="T-1023 INV003/INV004 burn-down: same disposition as the INV003 waiver above -- incidental prose, not an under-specified guaranteed behavior" -->

This page documents the WINDOWS half of `frob.deploy`'s generator
(`src/frob/deploy/_generate_windows.py`). The Linux/systemd half
(`install.sh`/`status.sh`/`uninstall.sh`, T-0257) is documented in
`docs/strata/host.md#the-deploy-generator` and `docs/commands/deploy.md`
-- neither is re-described here, only the windows target this ticket
adds.

## Windows generation

<!-- frob:describes src/frob/deploy/_generate_windows.py::windows_entries -->
<!-- frob:describes src/frob/deploy/_generate_windows.py::generate_windows_install_script -->
<!-- frob:describes src/frob/deploy/_generate_windows.py::generate_windows_status_script -->
<!-- frob:describes src/frob/deploy/_generate_windows.py::generate_windows_uninstall_script -->

`frob deploy generate` renders `install.ps1`/`status.ps1`/
`uninstall.ps1` alongside the bash target whenever the merged
`KernelModel` declares at least one node/store whose `HostManifest.
platform` (`std.host`, T-0261) is `HostPlatform.WINDOWS`
(`windows_entries` filters `sorted_manifest_entries` down to exactly
those). A linux-only model produces no `.ps1` files at all; a
windows-only model produces no bash -- `frob.deploy._generate.
generate_all` is the one call site that decides, per platform, which
scripts to include (`src/frob/deploy/_generate.py::generate_all`).

Per verb:

- **`install.ps1`** -- check-then-apply, same idempotency contract the
  bash target established: creates one service account per distinct
  `service_account` (`Install-ADServiceAccount` for a `gmsa`-marked
  identity, `New-LocalUser` otherwise). For a `service`-marked node whose
  manifest declares `bin_path` (`std.host`'s windows binPath/ImagePath
  vocabulary, T-0629), IDEMPOTENTLY CREATES the SCM service via `sc.exe
  create` with `binPath=` built from `bin_path`/`bin_path_args` when it
  is absent, then hardens it (SID type, required-privilege set via
  `sc.exe config`) the same as an already-existing service; a
  `service`-marked node with no `bin_path` declared falls back to the
  pre-T-0629 posture -- hardens the service only if it already exists,
  and emits a plain skip message (not a fabricated placeholder binary)
  when it is absent. It also applies each declared `acl` entry's NTFS
  grant (`icacls`), opens a firewall rule per declared `listens` port
  (`New-NetFirewallRule`), and -- when the SAME node also carries a
  `std.krb` manifest (`frob.strata.krb_manifest_for`, T-0262, NOT
  redefined here) -- registers its `spns` (`setspn`) and applies its
  `delegation` setting (`Set-ADAccountControl`/`Set-ADUser`).
- **`status.ps1`** -- per `service`-marked node, `sc.exe query` state
  plus a firewall-rule-present probe per declared `listens` port and a
  named-pipe existence probe per declared `pipe`.
- **`uninstall.ps1`** -- removes EXACTLY the manifest's own set: SCM
  service (when present), firewall rules, ACL grants, service accounts
  -- reverse order of install, same artifact-freeness contract the bash
  target's `uninstall.sh` documents.

## Same DEPLOY001 drift lock as bash

Every generated windows script's header carries the SAME
`frob.deploy._generate.manifest_digest` (computed over every platform's
`HostManifest` entries, not a second windows-only digest) that the bash
scripts carry -- one `DEPLOY001` drift lock covers all six filenames
`_drift.py::_GENERATED_FILENAMES` names. A committed `.ps1` that no
longer matches a fresh `generate_all` regeneration is flagged the same
way a stale `install.sh` is; a committed `.ps1` that the CURRENT model
no longer produces AT ALL (its windows manifest was removed) is ALSO
flagged, distinct from a content mismatch (`src/frob/deploy/_drift.py`'s
`filename not in fresh` branch).

## Scope and honesty notes (`generate` windows)

`std.host` now has a windows binPath/ImagePath vocabulary (`HostManifest.
bin_path`/`bin_path_args`, T-0629): when a `service`-marked node declares
`bin_path`, `install.ps1` idempotently `sc.exe create`s the service with
that ImagePath before hardening runs, rather than requiring the service
to pre-exist. A `service`-marked node that declares NO `bin_path` keeps
the pre-T-0629 posture -- it configures hardening on an ALREADY-EXISTING
service and says so plainly (rather than fabricating a placeholder
binary) when the service is absent.

Three v0 scope cuts remain, disclosed rather than silently dropped:

- **Required privileges** default to the empty (most restrictive) set
  (`sc.exe privs <name> ""`) -- `std.host` has no windows privilege
  vocabulary yet, mirroring the coarse `may`-kind capability join the
  bash target already documents for `CapabilityBoundingSet=`.
- **Deny-logon rights** (e.g. `SeDenyInteractiveLogonRight`) are not
  configured at all: there is no in-box, idempotently-checkable
  primitive for them without RSAT's `secedit` INF export/import
  round-trip. Deferred, not fabricated.
- **RBCD delegation** (`KrbDelegationKind.RBCD`) is not configured: it
  needs `PrincipalsAllowedToDelegateToAccount` plumbing beyond this
  generator's current scope. `none`/`constrained`/`unconstrained` are
  all implemented; `rbcd` emits a documented deferral note in the
  generated script instead of a fabricated command.

## Dependencies

Depends only on in-box Windows tools (`sc.exe`, `icacls`, `setspn.exe`,
`New-NetFirewallRule`/`Get-NetFirewallRule` from the in-box
`NetSecurity` module) for every non-AD operation. `Install-
ADServiceAccount`/`Uninstall-ADServiceAccount` (gMSA lifecycle) and
`Set-ADAccountControl`/`Set-ADUser` (Kerberos delegation flags) require
the `ActiveDirectory` RSAT module on a domain-joined host -- the same
class of assumed-present dependency the bash target already carries for
`useradd`/`systemctl`, not a new posture.

## See also

- `docs/strata/host.md#windows-surface-grammar` -- the `std.host`
  windows clauses (`platform`/`service_account`/`service`/`acl`/`pipe`,
  T-0261) this generator reads.
- `docs/strata/host.md#the-deploy-generator` -- the Linux/systemd
  target (T-0257) this module mirrors.
- `docs/strata/krb.md` -- `std.krb`'s `spn`/`delegation` vocabulary
  (T-0262), consumed here via `krb_manifest_for`, never redefined.
