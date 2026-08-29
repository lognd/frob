## Done report

Extract _assert_touched_files_lint_clean_pre_land's refusal tail (the
diagnostic-summary string build via ".".join()/. join() and the
sys.exit(1)) into a new helper, _refuse_pre_land_lint. That helper
owns both the string-formatting and the I/O together, and has zero
decision points of its own -- per T-3311's consolidating-split lesson,
an extraction only helps when it takes a whole concern with it. The
parent keeps every one of its own decision points (the touched-file/
baseline/new-violation checks are untouched) but no longer mixes I/O
or formatting with them, so ARCH103's mixed-concern-function check
(I/O + string-formatting + >=2 decision points in ONE body) no longer
fires on it.

This is the pre-land lint refusal guard T-3288 recently touched
(verified_landed kwarg) and T-3326 (check --fix scope threading) is
adjacent to but does not touch -- the refusal SHAPE (which violations
refuse, which are excluded as pre-existing) is byte-for-byte
unchanged; only the message-building/exit call moved to its own
function.

Measured before: gate reported 6 decision points at _land_cmd.py line
4286 (mixed-concern-function, ARCH103). Measured after (cache cleared,
no REPLAY): _assert_touched_files_lint_clean_pre_land no longer
appears anywhere in `frob check --only arch --json` output.

All 7 of this guard's existing tests (both files:
TestAssertTouchedFilesLintCleanPreLand in
test_ticket_work_and_land_finish.py and
test_ticket_land_lint_diff_attribution.py) pass unchanged, including
the genuinely-new-vs-pre-existing diff-attribution cases (T-3132) and
the baseline-unmeasurable fallback -- confirming the refusal behavior
is byte-identical. `frob test --base main` touched-set: 9/9 passed.

One pre-existing, unrelated failure was found and confirmed NOT
caused by this change: tests/test_ticket_work_and_land_finish.py::
TestBranchDriftGuard::test_branch_drift_before_final_commit_refuses_by_construction
fails identically with this file reverted to its pre-change state
(confirmed by checking out the unmodified file and rerunning the same
test in this worktree) -- not filed as a new ticket since it is
outside this ticket's scope (_land_cmd.py) to diagnose further here.

Full-repo `frob check --ticket T-3397` exceeded the available time
budget under heavy fleet contention (11+ concurrent checks running);
verified instead via targeted `--only arch` (fresh cache, no REPLAY)
and `--only release` (this ticket's own ARCH103 debt directive no
longer appears in REL001's findings; check_runner.py's ARCH103 entry
seen there belongs to T-3394, landed separately).

### Changed
```
 src/frob/app/ticket_runner/_land_cmd.py | 20 ++++++++++++++++++--
 tickets/T-3397/ticket.md                | 10 +++++++++-
 2 files changed, 27 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_ticket_work_and_land_finish.py::TestAssertTouchedFilesLintCleanPreLand::test_a_lint_error_in_a_touched_file_refuses_the_land` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestAssertTouchedFilesLintCleanPreLand::test_a_clean_touched_file_does_not_refuse` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestAssertTouchedFilesLintCleanPreLand::test_empty_touched_set_is_a_no_op` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land_lint_diff_attribution.py::TestAssertTouchedFilesLintCleanPreLand::test_genuinely_new_violation_still_refuses` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land_lint_diff_attribution.py::TestAssertTouchedFilesLintCleanPreLand::test_pre_existing_violation_that_merely_shifted_lines_does_not_refuse` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land_lint_diff_attribution.py::TestAssertTouchedFilesLintCleanPreLand::test_second_new_violation_sharing_identity_with_pre_existing_one_still_refuses` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land_lint_diff_attribution.py::TestAssertTouchedFilesLintCleanPreLand::test_baseline_unmeasurable_falls_back_to_file_scoped_refusal` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 18 error(s), 4083 warning(s), 897 waived
- error-findings: CYCLE001@src/frob/__init__.py, DEPR006@frob-deprecated-baseline.lock.json, DOC003@docs/commands/sys.md, DOC006@tickets/T-1382/ticket.md, DOC011@docs/modules/tickets.md, LEXCHECK001@src/frob/gates/_comment_placement.py, OPAQUE001@tests/unit/test_land_finish_idempotent.py, REL001@src/frob/__init__.py, REL001@src/frob/__main__.py, REL001@src/frob/app/check_runner.py, REL001@src/frob/process/_reap.py, REL001@src/frob/stats/_agentic.py, REL001@strata-core/src/graph/vmodel.rs, REL001@strata-core/src/parse/grammar_core.rs, REL001@tests/unit/test_conftest_suite_result_status.py, SELFAUDIT001@design, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
