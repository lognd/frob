## Done report

T-1078's incident: `_apply_release_bump_for_land` (src/frob/app/ticket_runner.py, out
of scope) writes pyproject.toml/CHANGELOG.md, calls `frob.release.stamp()` to write
`.frob-release.json`, but never checked `stamp()`'s Result -- if `stamp()` returns
`Err` (e.g. a worktree-lease mismatch), the manifest silently stays on its old
version while pyproject/CHANGELOG are already bumped and committed, desyncing the
release quartet. Every later land then re-derives an already-taken "next version"
from the stale manifest and refuses on the T-0992 monotonicity guard.

Fix, entirely inside this ticket's scope (src/frob/tickets/_land.py,
src/frob/release/__init__.py):

1. Atomic write (acceptance [0]): `frob.release.set_manifest_version(root, version)`
   rewrites ONLY the manifest's `version` field, preserving its `api` map. `_land.py`'s
   `_apply_release_bump` calls this immediately after any successful, monotonic bump
   (`_resync_release_manifest`, extracted for ARCH001) and stages `.frob-release.json`
   in the SAME step as the squash-apply commit -- regardless of whether the
   `bump_version` callback itself wrote the manifest correctly. This is a land-owned
   backstop, not a fix to the (out-of-scope) callback that has the actual silent-Result
   bug.

2. Refusal diagnostic (acceptance [1]): `_land.py` now also reads
   `.frob-release.json`'s version at `pre_land_tip` (`_read_root_manifest_version`,
   mirroring `_read_root_pyproject_version`'s git-object-read technique). When a
   monotonicity refusal fires AND the pre-land manifest version differs from the
   pre-land pyproject version, `_log_monotonicity_refusal` (extracted for ARCH001)
   emits a diagnostic naming the incoherent quartet explicitly and prescribing
   `frob release sync`, instead of the bare "not strictly greater" message.

Regression tests added to tests/test_ticket_land.py::TestReleaseBumpQuartetAtomicity:
- test_manifest_version_written_same_step_as_pyproject: a bump_version callback that
  bumps pyproject.toml but never touches .frob-release.json (models the actual
  incident) -- asserts the manifest is force-resynced to the new version, the api map
  survives, and both files land in the same commit.
- test_incoherent_quartet_refusal_names_desync: main's quartet is pre-desynced
  (pyproject 0.211.0, manifest 0.210.0); the bump callback computes 0.211.0 from the
  stale manifest, tripping T-0992's monotonicity guard -- asserts the refusal names
  the desync ("INCOHERENT"), points at "frob release sync", and cites both versions.

Filed: none (the ticket_runner.py ignored-Result bug that produced the original
incident is outside this ticket's scope; the fix here is a land-owned atomicity
backstop that makes the incident unreproducible regardless of that bug, per the
ticket's acceptance criteria).

### Changed
```
 docs/modules/release.md      |   9 ++-
 docs/modules/tickets.md      |  21 ++++++
 src/frob/release/__init__.py |  33 ++++++++++
 src/frob/tickets/_land.py    | 154 ++++++++++++++++++++++++++++++++++++-------
 tests/test_ticket_land.py    | 102 ++++++++++++++++++++++++++++
 tickets.md                   |  89 ++++++++++++++++++++++++-
 6 files changed, 381 insertions(+), 27 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestReleaseBumpQuartetAtomicity::test_manifest_version_written_same_step_as_pyproject` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestReleaseBumpQuartetAtomicity::test_incoherent_quartet_refusal_names_desync` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 814 warning(s), 420 waived
- error-findings: none (measured, zero errors)
