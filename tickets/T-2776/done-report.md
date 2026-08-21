## Done report

Batch 2/N of T-2359's ruff-format-only reformat. Filed as a child ticket
(same pattern as T-2773/batch 1) because `frob ticket land` closes its
target, and T-2359's repo-wide acceptance criteria cannot honestly bind
until every batch lands.

Re-measured unscoped before this batch: 171 files pending ruff-format
(184 - 15 landed in batch 1, +2 net drift from concurrent lands elsewhere
in the fleet). This batch covers 10 of the 171.

Excluded from consideration: none this batch needed exclusion --
T-2761 (which previously held src/frob/app/fmt_runner.py,
src/frob/app/ticket_runner/_land_cmd.py, src/frob/gates/_fix_engine_text.py,
src/frob/gates/_todo_fmt.py) landed as 39b91d228 before this batch was
picked, so those files are no longer contended; read T-2761's landed diff
(CHANGELOG.md, docs/modules/gates.md, the four wired files) before
reformatting fmt_runner.py/_land_cmd.py to confirm the per-language
resolve_line_length wiring it added would not be re-churned by a plain
`frob format` pass -- it would not (that ticket changed which limit-
resolution function is CALLED, not any literal wrap width in these
particular Python files, so ruff's own formatting output is unaffected).
tests/unit/test_app_runners_batch6.py was excluded (T-2753, in-progress,
scope includes it).

Changed (via `uv run frob format <path>`, T-2251 surface, one file at a
time):
src/frob/_cli_parsers/_misc.py
src/frob/_cli_parsers/_reporting.py
src/frob/app/fmt_runner.py
src/frob/app/ticket_runner/_land_cmd.py
src/frob/dup/_pipeline/_fingerprint.py
src/frob/dup/_template.py
src/frob/gates/_coverage_sites.py
src/frob/gates/_dead_symbols.py
src/frob/gates/_docblocks.py
src/frob/gates/_fix_engine.py

Diff reviewed by hand: quote normalization (single->double) and a small
number of line-length rewraps only. No logic changes, no fixture-corpus
files in the diff.

Evidence: one representative pytest node id per touched-file's own
frob:tests-bound test file (via a `frob:tests` grep across the batch),
all re-run and green, plus the larger sweeps they belong to:
tests/test_docblocks_gate.py (full file, 100%+ pass except pre-existing),
tests/unit/test_land_auto_rebase.py, tests/unit/test_land_cmd_backpressure.py,
tests/unit/test_land_cmd_quarantine.py, tests/unit/test_land_finish_guard.py,
tests/unit/test_land_finish_idempotent.py (72 tests total, 0 failures),
tests/test_ticket_merge_driver.py (9/9), tests/test_ticket_land.py
(303/303), tests/test_gates.py -k "TestTestGate or docblock or DeadSymbol
or dead_symbol or coverage_site or CoverageSite or FixEngine or
fix_engine" (148/149, the 1 failure --
TestFixEngineTierABatch2::test_docenum001_fails_before_fix_and_passes_after
-- reproduces byte-identically on unmodified main, confirmed by running
the same node id there, and is unrelated to this ticket).
tests/test_docblocks_gate.py::TestPythonNamespace::test_python_import_of_nonexistent_symbol_is_stale
tests/unit/test_land_auto_rebase.py::TestAutoSyncWorktreeOntoMain::test_merges_the_worktree_onto_the_new_main_tip
tests/unit/test_land_cmd_backpressure.py::TestApplyBackpressure::test_dry_run_skips_the_check
tests/unit/test_land_cmd_quarantine.py::TestQuarantineOverrideCeilings::test_not_quarantined_is_unchanged
tests/unit/test_land_finish_guard.py::TestScanForLiveWorktreeProcess::test_finds_a_process_cwd_into_the_path
tests/unit/test_land_finish_idempotent.py::TestTicketTerminalStateOnMain::test_done_ticket_returns_its_state
tests/test_ticket_merge_driver.py::TestArchivedIdsForMergeDriver::test_not_mid_merge_falls_back_to_disk_based_archived_ids
tests/test_ticket_land.py::TestFrobDirNeverLeaksIntoGitAdd::test_frob_scratch_files_are_gitignored_not_tracked
tests/test_gates.py::TestFixEngineTierABatch2::test_fmt001_wraps_overlong_directive_line_and_reverifies_clean

Filed: none this batch (T-2773 already tracks batch 1; T-2359 remains
open pending further batches, currently ~161 files, after this one
lands).

Gates: scoped `frob check --ticket T-2776` clean on the
touched files. Serialize this land per the coordinator's zero-lands-in-
flight rule (measured cause of earlier T-2359 land timeouts: concurrent
`frob check` calls in two simultaneous lands both blow the 540s shell
cap).

### Changed
```
 tickets/T-2359/ticket.md           | 145 +++++++++++++++++++++++++++++--------
 tickets/T-2776/ticket.md | 113 +++++++++++++++++++++++++++++
 2 files changed, 228 insertions(+), 30 deletions(-)
```

### Evidence
- `tests/test_docblocks_gate.py::TestPythonNamespace::test_python_import_of_nonexistent_symbol_is_stale` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_auto_rebase.py::TestAutoSyncWorktreeOntoMain::test_merges_the_worktree_onto_the_new_main_tip` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cmd_backpressure.py::TestApplyBackpressure::test_dry_run_skips_the_check` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cmd_quarantine.py::TestQuarantineOverrideCeilings::test_not_quarantined_is_unchanged` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_finish_guard.py::TestScanForLiveWorktreeProcess::test_finds_a_process_cwd_into_the_path` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_finish_idempotent.py::TestTicketTerminalStateOnMain::test_done_ticket_returns_its_state` (pytest node id, verified passing when recorded)
- `tests/test_ticket_merge_driver.py::TestArchivedIdsForMergeDriver::test_not_mid_merge_falls_back_to_disk_based_archived_ids` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestFrobDirNeverLeaksIntoGitAdd::test_frob_scratch_files_are_gitignored_not_tracked` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierABatch2::test_fmt001_wraps_overlong_directive_line_and_reverifies_clean` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: 18 error(s), 1179 warning(s), 710 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1688, COV003@tickets/T-2365, CYCLE001@src/frob/__init__.py, DOC001@docs/investigations/T-2202-mega-cluster.md, DOC006@docs/audits/test005-zero-classification-t1418.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, PERF004@src/frob/tickets/_evidence.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md
