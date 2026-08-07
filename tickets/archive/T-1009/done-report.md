## Done report

Changed:
- src/frob/release/__init__.py :: authoritative_version, rewrite_pyproject_version, changelog_skeleton_entry
- src/frob/app/release_runner.py :: run, _sync
- src/frob/__main__.py :: _add_release_parser (new `sync` subcommand)
- src/frob/gates/__init__.py :: release_gate, _rel002_coherence_violations, _uv_lock_version, _current_project_name
- src/frob/app/ticket_runner.py :: _root_release_manifest, _required_release_bump, _apply_release_bump_for_land, _write_release_bump
- Makefile :: upload (bump -> stamp -> sync -> commit all four artifacts)
- docs/modules/release.md, docs/modules/app.md, docs/modules/tickets.md, docs/modules/gates.md (AFFECT001 closure)

Authority flow: `.frob-release.json`'s `version` field is now the single
authority. `frob release sync` reads it (`authoritative_version`) and
regenerates `pyproject.toml` (`rewrite_pyproject_version`), `uv.lock`
(`uv lock`), and a CHANGELOG.md skeleton entry
(`changelog_skeleton_entry`) from it -- never the reverse. REL002 (new
rule, born ERROR, unconditional -- not suppressed under FROB_AGENT/land
ownership like REL001's bump half) names any artifact that disagrees
with the manifest. The land-time bump callback
(`_apply_release_bump_for_land`/`_required_release_bump` in
ticket_runner.py) now reads its baseline via `_root_release_manifest`
(`git show HEAD:.frob-release.json`, the same technique T-0992's
`_read_root_pyproject_version` guard already used for pyproject.toml)
instead of `frob.release.load_manifest`'s on-disk read, which could see a
stale worktree-carried `.frob-release.json` that rode the squash-apply
into root's working tree -- the T-1007 producer bug. `make upload` now
runs `frob release stamp` then `frob release sync` instead of hand-rolling
`uv lock`.

Evidence: 24 new/updated test ids (tests/test_release.py::
TestAuthoritativeVersion/TestRewritePyprojectVersion/
TestChangelogSkeletonEntry/TestReleaseGateCoherence,
tests/unit/test_ticket_runner_land_release.py::
TestApplyReleaseBumpForLand/TestRootReleaseManifestReadsRootHead,
tests/unit/test_app_runners_batch5.py::TestReleaseSyncRunner,
tests/test_ticket_land.py::TestRealCallbackStaleWorktreeManifest --
the real-callback T-0992-style regression through
`ticket_runner._land_bump_version_fn()`, proving the guard never fires
for the fixed callback). All 24 pass locally.

Filed: none (no out-of-scope discoveries beyond what T-1007 already
covered, now absorbed here).

Gates: `frob check --only gates-fast/gates-native/gates-security/lint/
static --ticket T-1009` all clean (0 errors) after re-sweep and an
ARCH102 waiver (release/__init__.py's sync helpers are the same
single-version-authority concern the module docstring already scopes
it to). `frob test --base main` selected 23 python tests including all
new evidence ids; the 5 pre-existing failures in that run
(TestLand::test_dry_run_lands_cleanly_and_leaves_no_trace,
TestMergeConflictOutsideLedger, TestWipCommitNormalizationOnlyDirty,
TestGitSubprocessFailures::test_unowned_deletions_diff_failure_after_merge,
TestDoneReportThenLandRealClosuresEndToEnd) are unrelated to this
ticket's scope -- reproduced standalone on an untouched test
(TestMergeConflictOutsideLedger) with no release/version code in its
path, caused by a nested `uv run pytest --collect-only` failing inside
this sandboxed worktree's tmp fixture trees (env artifact, matching the
"worktree natives artifact" class of pre-existing collection failures,
not a regression from this change).

### Changed
(no changed files detected)

### Evidence
- `tests/test_release.py::TestAuthoritativeVersion::test_reads_manifest_version` (pytest node id, verified passing when recorded)
- `tests/test_release.py::TestAuthoritativeVersion::test_no_manifest_is_err` (pytest node id, verified passing when recorded)
- `tests/test_release.py::TestRewritePyprojectVersion::test_rewrites_when_different` (pytest node id, verified passing when recorded)
- `tests/test_release.py::TestRewritePyprojectVersion::test_noop_when_already_matches` (pytest node id, verified passing when recorded)
- `tests/test_release.py::TestRewritePyprojectVersion::test_no_version_line_is_err` (pytest node id, verified passing when recorded)
- `tests/test_release.py::TestRewritePyprojectVersion::test_missing_file_is_err` (pytest node id, verified passing when recorded)
- `tests/test_release.py::TestChangelogSkeletonEntry::test_inserts_new_entry` (pytest node id, verified passing when recorded)
- `tests/test_release.py::TestChangelogSkeletonEntry::test_existing_entry_is_noop` (pytest node id, verified passing when recorded)
- `tests/test_release.py::TestChangelogSkeletonEntry::test_missing_changelog_is_noop` (pytest node id, verified passing when recorded)
- `tests/test_release.py::TestReleaseGateCoherence::test_clean_repo_has_no_rel002` (pytest node id, verified passing when recorded)
- `tests/test_release.py::TestReleaseGateCoherence::test_hand_edited_pyproject_fires_rel002` (pytest node id, verified passing when recorded)
- `tests/test_release.py::TestReleaseGateCoherence::test_hand_edited_uv_lock_fires_rel002` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_land_release.py::TestApplyReleaseBumpForLand::test_no_manifest_is_noop` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_land_release.py::TestApplyReleaseBumpForLand::test_bump_class_none_is_noop` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_land_release.py::TestApplyReleaseBumpForLand::test_bump_applies_writes_and_stamps` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_land_release.py::TestApplyReleaseBumpForLand::test_unreadable_graph_fails` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_land_release.py::TestRootReleaseManifestReadsRootHead::test_reads_head_manifest_not_worktree_disk_copy` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_land_release.py::TestRootReleaseManifestReadsRootHead::test_no_manifest_at_head_returns_none` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch5.py::TestReleaseSyncRunner::test_sync_no_manifest_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch5.py::TestReleaseSyncRunner::test_sync_regenerates_all_artifacts` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch5.py::TestReleaseSyncRunner::test_sync_already_in_agreement_is_quiet_but_still_locks` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch5.py::TestReleaseSyncRunner::test_sync_uv_lock_failure_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch5.py::TestReleaseSyncRunner::test_sync_bad_pyproject_version_line_exits_1` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestRealCallbackStaleWorktreeManifest::test_stale_worktree_manifest_still_lands_main_plus_one` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 24 passed (from 24 evidence id(s))
- gates: 0 error(s), 6025 warning(s), 406 waived
- error-findings: none (measured, zero errors)
