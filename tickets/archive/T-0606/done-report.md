## Done report

T-0606 wires the windows `service_account`/`acl`/`pipe` fields (T-0261)
into HOST001/HOST002 and `build_compromised_user_scenario`, closing the
gap `docs/strata/host.md#scope-boundary-what-is-not-built-here` and
T-0261's Done report documented: a windows-only node declaring solely
`service_account`/`acl`/`pipe` produced NO movement-impossibility
findings before this ticket, not because it was proven isolated but
because nothing read its windows-shaped facts.

Approach: generalize every identity/path/listening-surface join
`_host_isolation.py` performs to read EITHER platform's fields, never
branching the rule logic itself on `HostManifest.platform` (mirrors the
module's existing linux-only derivation discipline, T-0256/T-0272
precedent):

- `_identity_of`: a manifest's `runs_as` (linux) or `service_account`
  (windows) is the one identity `_nodes_by_user` groups nodes by.
- `_PathClaim` / `_owned_paths_by_user`: linux `owns` (POSIX MODE) and
  windows `acl` (NTFS DACL RULE, via a new local `_acl_grants_write`
  helper) merge into one per-user `path -> write_capable/descriptor`
  index. `shared-writable-path`, `root-unit-writable-by-user`, and
  `write-to-higher-trust-path` all read this merged index. `setuid`
  stays linux-only by construction (`_mode_has_setuid` cannot match an
  ACL-rule descriptor) -- an honest absence, not a fabricated windows
  equivalent, since NTFS has no bit that maps onto POSIX setuid.
- `_listening_surface_by_user`: linux `listens` (PORT) and windows
  `pipe` merge into one labeled set (`"port:9000"` / `"pipe:api-ipc"`)
  so `cross-user-socket` fires on a shared port, a shared pipe, or one
  of each; `host_movement_flows` mirrors the same union so
  `build_compromised_user_scenario`'s blast-radius claims stay
  non-vacuous over a shared windows pipe (T-0256's REJECT-round fix,
  extended).
- `_root_run_nodes`: a windows `service` with no `service_account`
  (SCM's LocalSystem default) is now treated as root-run, alongside the
  existing linux `unit` with no `runs_as`.
- `_scenarios.py::_compromised_user_nodes` now matches `service_account`
  in addition to `runs_as`.
- `group`/`sudoers` (T-0272) needed no change -- neither field was ever
  platform-gated.

docs/strata/host.md: added a `#windows-wiring-t-0606` subsection under
Movement-impossibility proofs, updated the scope-boundary bullet and the
`_host_isolation.py` See-also entry to drop the "NOT YET windows-aware"
wording.

## Done report

Changed:
- src/frob/strata/_host_isolation.py :: `_PathClaim`, `_identity_of`,
  `_acl_grants_write`, `_owned_paths_by_user`, `_listening_surface_by_user`
  (new); `_nodes_by_user`, `_owns_by_user` (docstring only, kept
  linux-only for `setuid`), `_shared_writable_path_violations`,
  `_shared_socket_violations`, `_writable_path_movement_flows`,
  `_shared_port_movement_flows`, `_root_run_nodes`,
  `_root_unit_writable_violations`, `_higher_trust_write_violations`,
  `_vertical_user_violations` (rewired to the platform-merged joins)
- src/frob/strata/_scenarios.py :: `build_compromised_user_scenario`,
  `_compromised_user_nodes` (docstrings + `service_account` match)
- docs/strata/host.md :: new `#windows-wiring-t-0606` section, updated
  scope-boundary and See-also entries
- tests/unit/strata/test_host_isolation.py :: new `TestWindowsHostIsolation`
  class (4 tests)

Evidence (bound to acceptance[0] via `frob ticket evidence --accepts 0`):
- tests/unit/strata/test_host_isolation.py::TestWindowsHostIsolation::test_shared_writable_acl_path_and_pipe_fire
- tests/unit/strata/test_host_isolation.py::TestWindowsHostIsolation::test_deny_acl_does_not_fire_shared_writable_path
- tests/unit/strata/test_host_isolation.py::TestWindowsHostIsolation::test_service_with_no_account_is_root_run
- tests/unit/strata/test_host_isolation.py::TestWindowsHostIsolation::test_compromised_windows_service_account_scenario

Full `pytest tests/unit/strata/test_host_isolation.py -q`: 25 passed.
`frob test --base main` (touched-set): [PASS] python exit=0.

Filed: none (no out-of-scope work discovered).

Gates: `frob check --ticket T-0606` run chunked by stage group (lint,
static, gates-fast, gates-native, gates-security) -- all PASS/clean for
this ticket's own findings. `gates-fast` surfaced one real SCOPE001
(`uv.lock` drifted outside declared scope from `uv run`/`make core`
invocations) -- reverted (`git checkout -- uv.lock`, land-owns the
lockfile per docs/guides/agent-playbook.md#4b) and reconfirmed clean.
`gates-fast`'s TEST003 findings on `src/frob/doctor.py` and
`src/frob/registry` are pre-existing, already-waived debt unrelated to
this ticket's scope (not touched by this change).

### Changed
```
 docs/strata/host.md                      |  73 ++++++--
 src/frob/strata/_host_isolation.py       | 291 +++++++++++++++++++++++++------
 src/frob/strata/_scenarios.py            |  24 +--
 tests/unit/strata/test_host_isolation.py | 125 +++++++++++++
 tickets.md                               |   6 +-
 5 files changed, 437 insertions(+), 82 deletions(-)
```

### Evidence
- `tests/unit/strata/test_host_isolation.py::TestWindowsHostIsolation::test_shared_writable_acl_path_and_pipe_fire` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_host_isolation.py::TestWindowsHostIsolation::test_deny_acl_does_not_fire_shared_writable_path` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_host_isolation.py::TestWindowsHostIsolation::test_service_with_no_account_is_root_run` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_host_isolation.py::TestWindowsHostIsolation::test_compromised_windows_service_account_scenario` (pytest node id, verified passing when recorded)
