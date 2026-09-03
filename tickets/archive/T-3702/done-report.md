## Done report

Changed: .claude/hooks/frob-timeout-guard.py::_HELP_OR_DRY_RUN_RE

Evidence: tests/test_hook_frob_timeout_guard.py::test_ticket_new_help_is_not_blocked, tests/test_hook_frob_timeout_guard.py::test_check_help_is_not_blocked exercise the help/dry-run detection path this constant backs; uv run frob check --only coverage confirms COV007 for frob-timeout-guard.py:63 is gone

Filed: none

Gates: frob check --only coverage clean of COV007

### Changed
```
 .claude/hooks/frob-timeout-guard.py |  1 -
 tickets/T-3702/done-report.md       | 23 +++++++++++++++++++++++
 tickets/T-3702/ticket.md            |  3 +++
 3 files changed, 26 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_hook_frob_timeout_guard.py::test_ticket_new_help_is_not_blocked` (pytest node id, verified passing when recorded)
- `tests/test_hook_frob_timeout_guard.py::test_check_help_is_not_blocked` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 4 error(s), 4282 warning(s), 915 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, DEPR006@frob-deprecated-baseline.lock.json, TICK011@tickets.md, WAIVE011@frob-ratchet.lock.json
