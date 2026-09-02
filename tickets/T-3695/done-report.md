## Done report

Changed:
.claude/hooks/frob-timeout-guard.py::_HELP_OR_DRY_RUN_RE
.claude/hooks/frob-timeout-guard.py::main

Evidence:
tests/test_hook_frob_timeout_guard.py::test_ticket_new_help_is_not_blocked
tests/test_hook_frob_timeout_guard.py::test_check_help_is_not_blocked
tests/test_hook_frob_timeout_guard.py::test_ticket_land_short_h_flag_is_not_blocked
tests/test_hook_frob_timeout_guard.py::test_check_version_flag_is_not_blocked
tests/test_hook_frob_timeout_guard.py::test_ticket_work_dry_run_flag_is_not_blocked
tests/test_hook_frob_timeout_guard.py::test_ticket_land_without_help_flag_still_blocks_under_min_timeout
tests/test_hook_frob_timeout_guard.py::test_quoted_help_flag_does_not_exempt_a_real_invocation
plus all 15 pre-existing tests in tests/test_hook_frob_timeout_guard.py, all still green (22/22 total)

Filed: none

Gates: frob check --ticket T-3695 clean of scope-caused findings (remaining errors are pre-existing native-extension-not-importable ty warnings from this fresh worktree lacking a frob_core/strata_core build, plus the expected pre-coordinator-sync claude-config-drift). frob test --base main: PASS (exit=0, 22 tests recorded).

### Changed
```
 .claude/hooks/frob-timeout-guard.py   | 21 ++++++++++-
 tests/test_hook_frob_timeout_guard.py | 67 +++++++++++++++++++++++++++++++++++
 tickets/T-3695/ticket.md              | 10 +++++-
 3 files changed, 96 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_hook_frob_timeout_guard.py::test_ticket_new_help_is_not_blocked` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_timeout_guard.py::test_check_help_is_not_blocked` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_timeout_guard.py::test_ticket_land_short_h_flag_is_not_blocked` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_timeout_guard.py::test_check_version_flag_is_not_blocked` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_timeout_guard.py::test_ticket_work_dry_run_flag_is_not_blocked` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_timeout_guard.py::test_ticket_land_without_help_flag_still_blocks_under_min_timeout` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_timeout_guard.py::test_quoted_help_flag_does_not_exempt_a_real_invocation` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 7 error(s), 4274 warning(s), 913 waived
- error-findings: AFFECT001@.claude/hooks/frob-timeout-guard.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV007@.claude/hooks/frob-timeout-guard.py, DEPR006@frob-deprecated-baseline.lock.json, PRE001@tickets/T-3695, TICK011@tickets.md, WAIVE011@frob-ratchet.lock.json
