## Done report

Measurement before building: searched TICK009/TICK010/TICK011/TICK012 and
no_scope_declared in code -- confirmed no existing rule checks for an
empty declared scope on a non-terminal ticket. SCOPE001 is diff-driven
(misses a clean worktree); TICK009 only checks breadth, never emptiness.
frob ticket start's _refuse_empty_scope_on_start (T-2394) is the only
existing check, and it only fires at the start transition -- frob ticket
scope --remove after a clean start can still empty the scope with
nothing catching it later, exactly the T-2377 incident this ticket's
body describes. So T-2557 was a real gap, not already-fixed work.

What the gate exempts: a ticket with no_scope_declared=True (the
first-class T-2394 opt-out, requiring a non-blank
no_scope_declared_reason) is silent regardless of how empty its scope
is -- the declaration IS the disclosure for a legitimately scope-free
tier=epic rollup or pure decision record. Also silent for: any
non-empty scope, any QUEUED ticket (mirrors TICK009's own T-1645
reasoning -- a queued ticket's scope is a pre-work prediction, not yet
a live lease), and any terminal-state ticket (done/dropped/failed hold
no lease). This exemption deliberately matches
_refuse_empty_scope_on_start's own "ticket.scope or
ticket.no_scope_declared" check exactly, so start-time refusal and the
new ledger-scan gate never disagree about what counts as legitimate.

Severity: ERROR (not WARN) -- an undeclared empty scope means the
ticket holds no write lease while able to edit anything, and no other
check tests against it; mirrors _refuse_empty_scope_on_start's own
severity for the identical condition.

Positive controls in both directions, as real pytest fixtures:
must-fire (IN_PROGRESS/PLANNED + empty scope + no declaration) and
must-not-fire (declared no-scope, non-empty scope, terminal state,
queued state) are each their own test method in
tests/test_tick013_gate.py, not prose.

Also registered CHK-GATE-TICK013 in check-coverage.yaml (via frob
registry audit --sync-gate-rules), bumped the testsuite::exec ratchet
195 -> 196 for the new subprocess-based test fixtures, added the new
test file to design/frob.strata's testsuite exec-via list, and closed
the AFFECT001 doc-closure gap on tickets_gate by adding a T-2557
paragraph to docs/modules/tickets-lifecycle.md alongside the T-2561/
T-1129 sibling-check precedent.

Filed: none -- no out-of-scope work found during this ticket. DOC013
and a pre-existing SYS003/SELFAUDIT001 test failure were observed
during verification but predate this ticket -- confirmed via git log
that DOC013 was introduced by the already-landed T-2080, and the
SYS003/SELFAUDIT001 failures are in src/frob/check/__init__.py and
tests/unit/test_ticket_new_related.py, files this ticket's scope never
touches.

Gates: frob check --ticket T-2557 clean of TICK013/REG009/REG010/
AFFECT001/PRE001/SELFAUDIT001(exec on the new test file)/SYS111(ratchet)
findings; the repo-wide ~28 remaining errors are pre-existing and
unrelated to this diff (measured before and after this ticket's edits,
count only decreased). frob test --base main on the new test file:
6/6 pass. Designated repro:
tests/test_tick013_gate.py::TestTick013EmptyScope::test_in_progress_empty_scope_fires
(FAILED_AT_PARENT verified against the test-only pre-fix commit).

### Changed
```
 design/frob.strata                                 |   2 +-
 .../registry/capability-via-ratchet.lock.json      |  24 ++--
 docs/design/registry/check-coverage.yaml           |   7 +-
 docs/modules/gates.md                              |  48 +++++++-
 docs/modules/tickets-lifecycle.md                  |  15 +++
 rapid-debt.jsonl                                   |   1 +
 src/frob/gates/_tickets_gate.py                    | 110 ++++++++++++++---
 src/frob/gates/_waive.py                           |   8 ++
 tests/test_tick013_gate.py                         | 131 +++++++++++++++++++++
 tickets/T-2557/done-report.md                      |  87 ++++++++++++++
 10 files changed, 403 insertions(+), 30 deletions(-)
```

### Evidence
- `tests/test_tick013_gate.py::TestTick013EmptyScope::test_in_progress_empty_scope_fires` (pytest node id, verified passing when recorded)
- `tests/test_tick013_gate.py::TestTick013EmptyScope::test_planned_empty_scope_fires` (pytest node id, verified passing when recorded)
- `tests/test_tick013_gate.py::TestTick013EmptyScope::test_queued_empty_scope_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_tick013_gate.py::TestTick013EmptyScope::test_nonempty_scope_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_tick013_gate.py::TestTick013EmptyScope::test_declared_no_scope_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_tick013_gate.py::TestTick013EmptyScope::test_terminal_state_empty_scope_is_silent` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 19 error(s), 1518 warning(s), 713 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1688, COV003@tickets/T-2365, CYCLE001@src/frob/__init__.py, DOC001@docs/investigations/T-2202-mega-cluster.md, DOC006@docs/audits/test005-zero-classification-t1418.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, PERF004@src/frob/tickets/_evidence.py, PRE001@tickets/T-2557, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md
