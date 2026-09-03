## Done report

Changed:
.claude/hooks/sync-claude-config.py::home_claude_missing (new)
.claude/hooks/sync-claude-config.py::_report_check (NOT_APPLICABLE branch)
src/frob/app/claude_runner.py::home_claude_missing (new)
src/frob/app/check_runner.py::_claude_config_drift_result (NOT_APPLICABLE branch)
tests/test_check_runner.py::TestClaudeConfigDriftStage
tests/unit/test_claude_runner.py::TestHomeClaudeMissing (new)
tests/unit/test_sync_claude_config_stale_guard_t3408.py::TestHomeClaudeMissingNotApplicable (new)

Evidence:
tests/test_check_runner.py::TestClaudeConfigDriftStage::test_not_applicable_when_home_claude_root_absent
tests/test_check_runner.py::TestClaudeConfigDriftStage::test_reports_drift_when_home_claude_present_but_file_differs
tests/unit/test_claude_runner.py::TestHomeClaudeMissing::test_true_when_home_claude_absent
tests/unit/test_claude_runner.py::TestHomeClaudeMissing::test_false_when_home_claude_present
tests/unit/test_sync_claude_config_stale_guard_t3408.py::TestHomeClaudeMissingNotApplicable::test_check_exits_0_when_root_absent_even_with_drifted_actions
tests/unit/test_sync_claude_config_stale_guard_t3408.py::TestHomeClaudeMissingNotApplicable::test_check_still_fails_when_root_present_but_file_differs

Root cause (measured on CI run 33439890956, both POSIX legs): the CLAUDE001
gate (frob.app.check_runner._claude_config_drift_result) treats EVERY
managed destination file that does not exist under ~/.claude as "drifted"
-- correct when ~/.claude is PRESENT but a file underneath it is stale or
missing, but on a CI runner (or any fresh machine) ~/.claude never exists
at all, so every one of the 9 managed files reads identically as "absent"
and the whole stage FAILs even though there is nothing to reconcile
against on that machine.

Fix: added a `home_claude_missing()` predicate to the canonical hook
script (.claude/hooks/sync-claude-config.py), its frob.app.claude_runner
adapter, and used it in both _claude_config_drift_result (frob check's
own CLAUDE001 stage) and the hook's own --check reporting to report
NOT_APPLICABLE (a single info-severity diagnostic, exit_code=0) when the
whole ~/.claude root is absent, instead of one CLAUDE001 error per
managed file. A genuinely missing SOURCE file still errors regardless (a
real repo-tree defect, unrelated to whether ~/.claude exists), and a
PRESENT-but-drifted ~/.claude is completely unaffected -- still FAILs
exactly as before. The existing test_reports_drift_when_managed_copy_absent
(whose own fixture never created ~/.claude, i.e. exercised exactly this
false-positive shape) was renamed test_not_applicable_when_home_claude_
root_absent and its assertions updated to the new, correct verdict; a
new sibling test proves the present-but-drifted case still FAILs.

Filed: none

Gates: frob check --ticket T-3600 clean on gate:SCOPE/gate:PRE (sweep
refreshed). Repo-wide failures from an unscoped run are pre-existing
(T-3590). BUG002 designation forced (--designate-repro-force) since the
renamed test cannot be checked pre-land per T-2025's own documented
limitation; manually verified via the discharge/regression test pairs
above that the fix's behavior split is correct (present-but-drifted
still fails, root-absent no longer does).
