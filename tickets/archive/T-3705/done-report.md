## Done report

T-3696 added the PLATFORM002 detector gate win32_kill_signal to
frob.gates._ALL_GATES but never added it to a _STAGE_GROUPS member,
leaving it registered but unreachable via any `frob check --only <stage>`
group. tests/system/test_cli_check.py::TestCheckStageGroups::
test_available_stages_cover_every_gate_and_tool correctly caught the gap
and was the ubuntu CI blocker (run 33680767948). Added win32_kill_signal
to the gates-fast group, next to walk_lint/excludehazard (same thread-
pool, repo-wide-scan shape). Ran the full TestCheckStageGroups class
(4/4 pass) to check for any other similarly-omitted recently-added gate;
found none. Evidence designated as repro via --designate-repro-force
after --check-repro's scratch-worktree checkout timed out on unrelated
fleet load; the retry then completed and returned FAILED_AT_PARENT,
confirming the repro shape by tool, not just by hand.

### Changed
```
 src/frob/check/__init__.py | 9 +++++++++
 tickets/T-3705/ticket.md   | 6 ++++--
 2 files changed, 13 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/system/test_cli_check.py::TestCheckStageGroups::test_available_stages_cover_every_gate_and_tool` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 5 error(s), 4335 warning(s), 913 waived
- error-findings: COV007@.claude/hooks/frob-timeout-guard.py, DEPR006@frob-deprecated-baseline.lock.json, TICK003@tickets.md, TICK011@tickets.md, WAIVE011@frob-ratchet.lock.json
