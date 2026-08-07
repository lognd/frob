---
id: T-1358
title: T-1340 land desynced .frob-release.json from pyproject.toml, blocking all lands
state: done
kind: bug
origin: human
created: '2026-07-31'
priority: critical
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land_release.py
- tests/unit/test_land_release_coherence.py
- docs/modules/tickets.md
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_land_release_coherence.py
  reason: regression test for T-1358 quartet coherence fix
  actor: logan
  at: '2026-08-01'
- op: add
  glob: docs/modules/tickets.md
  reason: 'AFFECT001: _apply_release_bump changed, doc edge lives here'
  actor: logan
  at: '2026-08-01'
- op: add
  glob: design/frob.strata
  reason: frob sys sync-interface touched this to register new test symbols
  actor: logan
  at: '2026-08-01'
evidence:
- tests/unit/test_land_release_coherence.py::TestReadWorkingVersions::test_reads_pyproject_version_from_disk
- tests/unit/test_land_release_coherence.py::TestReadWorkingVersions::test_missing_pyproject_is_none
- tests/unit/test_land_release_coherence.py::TestReadWorkingVersions::test_reads_manifest_version_from_disk
- tests/unit/test_land_release_coherence.py::TestReadWorkingVersions::test_missing_manifest_is_none
- tests/unit/test_land_release_coherence.py::TestReadWorkingVersions::test_malformed_manifest_is_none
- tests/unit/test_land_release_coherence.py::TestEnsureReleaseQuartetCoherent::test_already_coherent_is_noop
- tests/unit/test_land_release_coherence.py::TestEnsureReleaseQuartetCoherent::test_diverged_versions_force_resync
- tests/unit/test_land_release_coherence.py::TestEnsureReleaseQuartetCoherent::test_missing_manifest_is_noop
- tests/unit/test_land_release_coherence.py::TestApplyReleaseBumpCoherenceGuard::test_callback_reports_none_but_pyproject_already_diverged
- tests/unit/test_land_release_coherence.py::TestApplyReleaseBumpCoherenceGuard::test_callback_reports_new_version_normally
designated_repro_test: null
threat: null
component: null
---
Observed 2026-07-31 while landing T-1348: T-1340's land (commit b614d46b)
bumped pyproject.toml's version 0.289.0 -> 0.290.0 but never updated
.frob-release.json, which stayed at 0.289.0. This desynced the release
quartet and refused (T-0992 monotonicity assertion, ReleaseBumpFailed)
EVERY subsequent land that needed a version bump -- a repo-wide land
outage, not a per-ticket issue.

Repaired directly on main (commit b863249d, `frob release stamp`) since
the fix is narrow (manifest version + T-1340's own unrecorded new-symbol
hashes) and the pre-commit land-owned-file guard does not cover
.frob-release.json (only CHANGELOG.md/uv.lock/pyproject.toml's version
line) -- confirmed this repair does not need FROB_LAND_INTERNAL.

ROOT CAUSE NOT YET DIAGNOSED: `_apply_release_bump`/`_resync_release_
manifest` (src/frob/tickets/_land_release.py, T-1078) is SUPPOSED to
force-resync the manifest to `new_version` in the SAME land step that
bumps pyproject.toml, specifically to prevent this exact desync. T-1340's
land commit shows only pyproject.toml/CHANGELOG.md changed, not
.frob-release.json -- meaning either the resync step did not run, ran
and failed silently, or T-1340 was landed via a path that bypasses
`_apply_release_bump` entirely (a manual/coordinator squash rather than
`frob ticket land`'s own CLI). Find out which, and if it is the former,
this is a live regression in T-1078's own guarantee and needs a real fix,
not just this one-off repair.

Suggested acceptance: reproduce the exact conditions of T-1340's land (or
audit its actual land invocation/log) to identify why `_resync_release_
manifest` did not fire or did not stick, and add a regression test
covering that specific path.