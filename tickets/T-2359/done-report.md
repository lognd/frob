## Done report

Changed: none -- zero-diff verification batch (all 138 originally-filed
files, plus every file touched across 16 prior landed batches, are already
ruff-format clean).

Re-measured 2026-08-21 in a fresh worktree (post T-2818 land, which touched
the previously-blocking `tests/unit/test_coordinator_scripts.py`):
`uv run ruff format --check .` -> exit 0, "1202 files already formatted",
0 files needing reformat.

Characterization: this closes the epic. The 10 scope entries the requeued
ticket carried were stale leftovers from earlier batches (per the
coordinator's own note) and were removed; `no_scope_declared=true` is now
set since no file edits are required to satisfy this final measurement.

Acceptance criteria restored to their original repo-wide form (the batching
amendments were correctly time-boxed placeholders per their own text:
"re-added once the final batch lands and the repo-wide criterion is
genuinely true"). All three now bind:
  [0] diff review (no semantic changes, no fixture corpus) -- vacuously true,
      no diff exists in this batch
  [1] test suite passes unchanged -- 191 tests across
      test_pyfmt_runner/test_app_runners/test_check pass clean
      (SUITE-RESULT: exitstatus=0 collected=191 failed=0)
  [2] ruff format --check . reports zero files needing reformat -- measured
      directly, exit 0

Evidence: tests/unit/test_pyfmt_runner.py::TestRun::test_default_delegates_to_run_ruff_autofix,
tests/unit/test_pyfmt_runner.py::TestRuffFormatWriteOnly::test_missing_binary_yields_typed_result,
plus 11 pre-existing evidence_scope node ids retained from earlier batches
(test_app_runners.py, test_app_runners_batch7.py, test_profile_runner.py,
test_app_sys_capacity.py, test_app_sys_threats.py, test_app_sys_trace.py,
test_telemetry.py, test_check.py, test_new_ticket_scope_overlap_warning.py,
test_ticket_new_related.py, test_ticket_new_scope_plausibility.py).

Filed: none -- no out-of-scope work discovered.

Gates: no code changed; `frob check` unaffected by this batch. Not run as a
blocking gate here since scope is empty (no_scope_declared=true); relying
on the direct ruff-format-check measurement plus the test-suite run above
as the ticket's own positive controls, per its filed acceptance criteria.

### Changed
```
 tickets/T-2359/ticket.md | 154 +++++++++++++++++++++++++++++++++++++++++------
 1 file changed, 134 insertions(+), 20 deletions(-)
```

### Evidence
- `tests/unit/test_app_runners.py::TestMapRunner::test_text_mode_logs_summary` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketRunnerDispatch::test_unknown_command_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_profile_runner.py::TestProfileRunnerShow::test_show_reports_configured_and_effective` (pytest node id, verified passing when recorded)
- `tests/unit/test_pyfmt_runner.py::TestRun::test_default_delegates_to_run_ruff_autofix` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_sys_capacity.py::TestSysCapacity::test_no_population_reports_current_violations` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_sys_threats.py::TestSysThreats::test_no_boundary_prints_every_violation` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_sys_trace.py::TestSysTrace::test_trace_prints_witness_path_to_destination` (pytest node id, verified passing when recorded)
- `tests/test_telemetry.py::test_append_event_writes_one_json_line` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestCheckResultCounts::test_total_errors_sums_across_results` (pytest node id, verified passing when recorded)
- `tests/unit/test_new_ticket_scope_overlap_warning.py::TestScopeOverlapWarnings::test_overlapping_scope_names_the_other_ticket_and_path` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_new_related.py::TestRelatedTicketsSearch::test_finds_an_archived_close_title_match` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_new_scope_plausibility.py::TestScopePlausibility::test_implausible_scope_warns_loudly` (pytest node id, verified passing when recorded)
- `tests/unit/test_pyfmt_runner.py::TestRuffFormatWriteOnly::test_missing_binary_yields_typed_result` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 13 passed (from 13 evidence id(s))
- gates: 19 error(s), 566 warning(s), 716 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, CYCLE001@src/frob/__init__.py, DOC006@docs/audits/test005-zero-classification-t1418.md, DOC011@docs/investigations/T-2796-backlog-reproduction.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, PERF004@src/frob/tickets/_evidence.py, REG002@docs/design/registry/check-coverage.yaml, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md

### Acceptance amendments
- [2] remove: removed 'given the test suite, when it runs after the reformat, then it passes unchanged' (reason: batched execution (coordinator directive): acceptance criteria as filed assume a single-shot repo-wide reformat, but 184 files across many in-flight worktrees requires landing in small disjoint batches to avoid locking the fleet. Re-added once the final batch lands and the repo-wide criterion is genuinely true.; logan, 2026-08-20)
- [1] remove: removed 'given the format-only commit, when its diff is reviewed, then it contains no semantic changes and no fixture-corpus files' (reason: batched execution: same rationale as index-2 removal, this criterion also assumes single-shot completion; re-added on the final batch; logan, 2026-08-20)
- [0] remove: removed 'given the repo after this lands, when ruff format --check . runs, then zero files need reformatting' (reason: batched execution: same rationale; final-batch land will re-add a criterion bound to a genuine repo-wide ruff-format-clean measurement; logan, 2026-08-20)
- [2] remove: removed 'given the test suite, when it runs after the reformat, then it passes unchanged' (reason: duplicate of newly re-added index 5 (final-batch criterion); the earlier 2026-08-20 removal amendment was documentation-only and never actually stripped the entry, so both copies existed; logan, 2026-08-21)
- [1] remove: removed 'given the format-only commit, when its diff is reviewed, then it contains no semantic changes and no fixture-corpus files' (reason: duplicate of newly re-added index (final-batch criterion); same stale-removal-was-documentation-only issue; logan, 2026-08-21)
- [1] remove: removed 'given the repo after this lands, when ruff format --check . runs, then zero files need reformatting' (reason: duplicate final-batch criterion left over from the earlier documentation-only removal; collapsing to one copy; logan, 2026-08-21)
- [0] remove: removed 'given the repo after this lands, when ruff format --check . runs, then zero files need reformatting' (reason: duplicate of newly re-added index (final-batch criterion); same stale-removal-was-documentation-only issue; logan, 2026-08-21)
