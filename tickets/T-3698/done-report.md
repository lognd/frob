## Done report

_pid_alive delegated to frob.process._pid_liveness.pid_alive, removing the
os.kill(pid, 0) win32 Ctrl+C-broadcast footgun from the gate-execution
path (same class of bug T-3686 fixed for frob.check._pid_alive).

Evidence:
- tests/gates_suite/test_fix_engine.py::TestPidAlive.test_pid_alive_delegates_to_shared_process_liveness_probe
  (pins the delegation: os.kill monkeypatched to raise, _pid_liveness.pid_alive
  monkeypatched to record calls -- proves no os.kill and correct liveness
  result via the delegated probe, per the ticket's acceptance criterion)
- tests/gates_suite/test_fix_engine.py::TestPidAlive.test_pid_alive_true_for_self
- tests/gates_suite/test_fix_engine.py::TestPidAlive.test_pid_alive_false_for_implausible_pid
- frob check --only win32_kill_signal: 0 PLATFORM002 findings, 0 waivers on
  src/frob/gates/_fix_engine_shared.py -- the interim frob:waive PLATFORM002
  removed as part of this fix, no longer needed
- frob test --base main: exit=0, 5 python test outcomes recorded

Filed: none (no out-of-scope work found)

Gates: frob check --ticket T-3698 clean on SCOPE/PRE/DOC/DRIFT (the gates
this ticket's scope governs); remaining errors (DEPR006, TICK011, WAIVE011,
COV007 on an unrelated hook file, claude-config-drift) are pre-existing
repo-wide/environment findings unrelated to this ticket's scope.

### Changed
```
 src/frob/gates/_fix_engine_shared.py | 53 ++++++++++++++++++------------------
 tests/gates_suite/test_fix_engine.py | 45 ++++++++++++++++++++++++++++++
 tickets/T-3698/done-report.md        | 38 ++++++++++++++++++++++++++
 tickets/T-3698/ticket.md             | 18 ++++++++++--
 4 files changed, 126 insertions(+), 28 deletions(-)
```

### Evidence
- `tests/gates_suite/test_fix_engine.py::TestPidAlive::test_pid_alive_delegates_to_shared_process_liveness_probe` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_fix_engine.py::TestPidAlive::test_pid_alive_true_for_self` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_fix_engine.py::TestPidAlive::test_pid_alive_false_for_implausible_pid` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 5 error(s), 4288 warning(s), 912 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV007@.claude/hooks/frob-timeout-guard.py, DEPR006@frob-deprecated-baseline.lock.json, TICK011@tickets.md, WAIVE011@frob-ratchet.lock.json
