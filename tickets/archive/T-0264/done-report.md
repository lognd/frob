## Done report

T-0264: added the windows generation target for `frob deploy generate`,
mirroring the linux (T-0257) generator's check-then-apply contract for
`HostPlatform.WINDOWS` manifests.

New module `src/frob/deploy/_generate_windows.py`:
- `windows_entries` filters `sorted_manifest_entries` to WINDOWS-platform
  entries only.
- `generate_windows_install_script`: creates one service account per
  distinct `service_account` (local account or gMSA via
  `Install-ADServiceAccount`), hardens an already-existing `service`-marked
  node's SCM service (SID type, required-privilege set) via `sc.exe
  config`, applies NTFS ACL grants (`icacls`), opens firewall ports
  (`New-NetFirewallRule`), and -- when the same node also has a `std.krb`
  manifest -- registers SPNs (`setspn`) and applies delegation flags
  (`Set-ADAccountControl`/`Set-ADUser`).
- `generate_windows_status_script`: SCM state (`sc.exe query`) plus a
  firewall-rule-present probe per `listens` port and a named-pipe probe
  per `pipe`.
- `generate_windows_uninstall_script`: removes exactly the manifest set in
  reverse order -- service, firewall rules, ACL grants, service accounts.

`src/frob/deploy/_generate.py::generate_all` now emits `install.ps1`/
`status.ps1`/`uninstall.ps1` alongside the bash trio whenever the model
declares at least one windows entry, sharing the SAME `manifest_digest`
(computed over every platform) for the drift-lock header.

`src/frob/deploy/_drift.py`'s DEPLOY001 filename list grew the three
`.ps1` names; a committed `.ps1` the current model no longer produces at
all is now also flagged as drift (previously would have KeyError'd).

Honest v0 scope cuts, documented in `docs/modules/deploy.md` (new file,
this ticket's scope) and inline: `std.host` has no windows binPath
vocabulary yet, so a `service`-marked node's SCM service is hardened only
if it already exists, never created from scratch; required-privilege
sets default to empty (no windows privilege vocabulary yet); deny-logon
rights are documented-deferred (no in-box idempotent primitive without
RSAT secedit); RBCD delegation is documented-deferred
(needs PrincipalsAllowedToDelegateToAccount plumbing).

New test files: tests/unit/deploy/test_generate_windows.py (18 tests) and
additions to tests/unit/deploy/test_drift.py (2 new tests: a committed
`.ps1` no longer produced by the model is flagged; a model WITH a windows
manifest regenerates all six files clean).

REL001 (public API version bump) fires repo-wide since new public symbols
were added; pyproject.toml is out of this ticket's scope, left for the
coordinator's land-time version bump per the established landing workflow.

### Changed
```
 tickets.md | 806 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++-
 1 file changed, 797 insertions(+), 9 deletions(-)
```

### Evidence
(no evidence recorded)
