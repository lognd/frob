## Done report

Extended frob.tickets.land with two optional callables (bump_version,
rebuild_natives), folding the two remaining coordinator-plumbing steps
T-0479 did not cover into the same one-command land: a REL001
version-bump/stamp step (frob.release.diff_class/required_version
against the tracked manifest; rewrites pyproject.toml + CHANGELOG.md +
.frob-release.json, staged into the same landing commit) and a
native-rebuild trigger (runs `make core` when the landed changeset
touches frob-core/ or strata-core/). Both run after the squash-apply is
staged and before the T-0463 completeness assertion, so a bump-callback
failure unwinds the squash exactly like any other land failure; a
rebuild-callback failure is best-effort (logged, non-blocking, alongside
the existing T-0248 stale-native warning). frob.tickets stays free of
frob.release/frob.graph/subprocess access (docs/rework.md
cycle-avoidance): the actual CLI implementations
(_apply_release_bump_for_land, _write_release_bump,
_land_rebuild_natives_fn) live in frob.app.ticket_runner and are wired
into `frob ticket land`'s default call, matching the existing
collected/passed/covers_scope pattern from T-0398/D-05. LandReport grew
release_bumped_to and natives_rebuilt fields, both reported by the CLI.

### Changed
```
 .frob-release.json                            |   5 +-
 CHANGELOG.md                                  |  43 ++++++
 docs/modules/tickets.md                       |  53 ++++++-
 pyproject.toml                                |   2 +-
 src/frob/app/ticket_runner.py                 | 209 +++++++++++++++++++++++++-
 src/frob/tickets/__init__.py                  | 102 +++++++++++++
 src/frob/tickets/_land.py                     | 132 +++++++++++++++-
 src/frob/tickets/_models.py                   |   9 ++
 tests/test_ticket_land.py                     | 167 ++++++++++++++++++++
 tests/unit/test_ticket_runner_land_release.py | 182 ++++++++++++++++++++++
 tests/unit/test_ticket_store.py               |  68 +++++++++
 tickets.md                                    |  88 ++++++++++-
 uv.lock                                       |   2 +-
 13 files changed, 1047 insertions(+), 15 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestReleaseBump::test_bump_applied_and_reported` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestReleaseBump::test_no_bump_needed_reports_none` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestReleaseBump::test_bump_failure_unwinds_squash` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestReleaseBump::test_no_callback_is_noop` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestRebuildNatives::test_invoked_when_native_source_touched` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestRebuildNatives::test_skipped_when_no_native_source_touched` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestRebuildNatives::test_rebuild_failure_does_not_block_land` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_land_release.py::TestWriteReleaseBump::test_rewrites_version_and_prepends_changelog_entry` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_land_release.py::TestWriteReleaseBump::test_missing_version_line_fails` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_land_release.py::TestApplyReleaseBumpForLand::test_no_manifest_is_noop` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_land_release.py::TestApplyReleaseBumpForLand::test_bump_class_none_is_noop` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_land_release.py::TestApplyReleaseBumpForLand::test_bump_applies_writes_and_stamps` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_land_release.py::TestApplyReleaseBumpForLand::test_unreadable_graph_fails` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_land_release.py::TestLandRebuildNativesFn::test_success_returns_true` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_land_release.py::TestLandRebuildNativesFn::test_failure_returns_false_and_logs` (pytest node id, verified passing when recorded)
