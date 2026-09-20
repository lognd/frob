## Done report

Evidence:
tests/unit/test_conftest_suite_result_status.py::TestSuiteResultDidNotComplete::test_sessionfinish_labels_did_not_complete_runs
tests/ticket_land_suite/test_land_lock.py::TestLandLockHolderMetadataAndTimeout::test_holder_metadata_written_on_acquire
tests/test_tickets_mutation_evidence.py::TestTouchedPythonFiles::test_matches_base_ref_tip_true_for_identical_content
tests/test_tickets_mutation_evidence.py::TestTouchedPythonFiles::test_already_landed_sibling_content_excluded
tests/system/test_cli_ticket.py::TestTicketAttachNonInteractive::test_attach_without_path_fails_fast_off_tty
tests/test_worktree_guard.py::TestAgentEnvStdoutPurity::test_bare_eval_succeeds_with_no_filtering

All 103 tests in the 5 originally-affected files (test_conftest_suite_result_status.py,
test_land_lock.py, test_tickets_mutation_evidence.py, test_cli_ticket.py,
test_worktree_guard.py) re-run clean on Linux after rebase onto main: 0 failed, 1
skipped (pre-existing, unrelated).

Filed: T-4029 (already filed on this branch before this session started;
preserved, not touched -- needs a src/frob/tickets/_land.py fix outside this
ticket's test-only scope, left for a future ticket).

Gates: frob check --ticket T-4028 clean apart from:
  - CROSSTICKET001 (5): this ticket's scope legitimately overlaps T-3936's
    declared (broader) scope on the same shared test files -- intentional,
    since this is a deliberate narrow carve-out of 6 of T-3936's 19 Windows
    failures landing ahead of the rest. Land with --allow-cross-ticket.
  - SCOPE002 (6, gate:SCOPE, tickets.md): scope-closure nudges pointing at
    src/frob/tickets/_land.py, src/frob/tickets/_mutation_evidence.py,
    tests/conftest.py, and three test fixture files reached via pre-existing
    frob:tests bindings and private-helper fakes already present in the
    touched test files (not introduced by this change). SCOPE002 is
    documented (src/frob/gates/__init__.py::_scope002_violations) as
    Severity.WARN, "a nudge, not a hard block ... must never block a ticket
    that legitimately intends a narrower slice than its own doc/call graph
    suggests" -- confirmed non-blocking at the real land gate
    (frob ticket land --dry-run proceeded past it to the evidence/Done-
    report check). Widening scope to close it was tried and reverted: it
    cascades into roughly 360 further doc-edge closure warnings over
    unrelated src/frob/tickets/_land.py symbols, a worse outcome than
    leaving the nudge open. Not waived line-by-line since the rule itself
    is documented non-blocking.
  - DRIFT001 (src/frob/xref/__init__.py::xref): pre-existing on main,
    unrelated to this ticket (file untouched by this branch); confirmed the
    working tree for this file is byte-identical to main's.

### Changed
```
 tests/system/test_cli_ticket.py                 | 17 +++++++++++
 tests/test_tickets_mutation_evidence.py         | 38 +++++++++++++++++++------
 tests/test_worktree_guard.py                    | 10 +++++++
 tests/ticket_land_suite/test_land_lock.py       | 14 ++++++++-
 tests/unit/test_conftest_suite_result_status.py | 35 +++++++++++++++++++++++
 tickets/T-4028/ticket.md              |  7 +++++
 tickets/T-4029/ticket.md              | 28 ++++++++++++++++++
 7 files changed, 140 insertions(+), 9 deletions(-)
```

### Evidence
- `tests/unit/test_conftest_suite_result_status.py::TestSuiteResultDidNotComplete::test_sessionfinish_labels_did_not_complete_runs` (pytest node id, verified passing when recorded)
- `tests/ticket_land_suite/test_land_lock.py::TestLandLockHolderMetadataAndTimeout::test_holder_metadata_written_on_acquire` (pytest node id, verified passing when recorded)
- `tests/test_tickets_mutation_evidence.py::TestTouchedPythonFiles::test_matches_base_ref_tip_true_for_identical_content` (pytest node id, verified passing when recorded)
- `tests/test_tickets_mutation_evidence.py::TestTouchedPythonFiles::test_already_landed_sibling_content_excluded` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_ticket.py::TestTicketAttachNonInteractive::test_attach_without_path_fails_fast_off_tty` (pytest node id, verified passing when recorded)
- `tests/test_worktree_guard.py::TestAgentEnvStdoutPurity::test_bare_eval_succeeds_with_no_filtering` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 7 error(s), 4404 warning(s), 930 waived
- error-findings: CROSSTICKET001@tests/system/test_cli_ticket.py, CROSSTICKET001@tests/test_tickets_mutation_evidence.py, CROSSTICKET001@tests/test_worktree_guard.py, CROSSTICKET001@tests/ticket_land_suite/test_land_lock.py, CROSSTICKET001@tests/unit/test_conftest_suite_result_status.py, DRIFT001@src/frob/xref/__init__.py, SCOPE002@tickets.md
