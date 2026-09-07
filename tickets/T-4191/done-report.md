## Done report

Added follow_up=\"T-4151\" to the existing WIRE001 waiver on
_sync_fixture_project in tests/unit/test_flag_coverage_gate.py, so
WIRE002's follow-up-attribute requirement is satisfied without
inventing a new ticket. T-4151 already owns reconsidering WIRE001's
call-reachability mechanism and its inability to see test-internal
callers, which is exactly the reason this waiver exists.

Rewrapped the edited waiver's continuation lines with
`frob format --directives` (invoked as `frob fmt`) after the added
attribute pushed line 33 past 88 cols; verified the comment marker,
backslash continuations, and both ticket ids (T-4151, T-4171) survived
the rewrap and the module still parses (ast.parse) and collects (10
tests pass across the fixture file and the live-repo WIRE002 test).

Filed: none (per ticket instruction: point the follow-up at T-4151,
do not invent one).

Recorded the fixture-vs-production scoping observation on T-4151's
body via `frob ticket body --append`, as this ticket's acceptance
required.

Bound acceptance [1] to the live-repo WIRE002 test and acceptance [2]
to test_wire002_fires_when_follow_up_ticket_missing, which proves a
WIRE001 waiver on a production symbol with no follow-up is still
refused -- the requirement this fix must not weaken.

Gates: gate:WIRE clean (0 errors). Ticket-scoped diff checks (FMT,
PRE, SCOPE-diff, COV002/TODO001) clean for this change. Remaining
--ticket-scoped errors (ARCH103, COV001, DRIFT001/002, SCOPE002 on
pre-existing frob:tests targets) are repo-wide/pre-existing per the
scope-note and unrelated to tests/unit/test_flag_coverage_gate.py;
none introduced by this diff.

### Changed
```
 tests/unit/test_flag_coverage_gate.py |  6 ++---
 tickets/T-4151/ticket.md              |  9 +++++++
 tickets/T-4191/done-report.md         | 48 +++++++++++++++++++++++++++++++++++
 tickets/T-4191/ticket.md              | 14 +++++++---
 4 files changed, 71 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/unit/test_flag_coverage_gate.py::TestFlagCoverageGate::test_must_now_fire_reports_the_genuinely_dropped_flag` (pytest node id, verified passing when recorded)
- `tests/unit/test_flag_coverage_gate.py::TestFlagCoverageGate::test_must_still_pass_when_everything_is_forwarded` (pytest node id, verified passing when recorded)
- `tests/unit/test_flag_coverage_gate.py::TestFlagCoverageGate::test_this_repos_own_frob_toml_reports_zero` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_wire002_live_repo.py::test_wire002_zero_against_live_repo` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_wire.py::TestWireGate::test_wire002_fires_when_follow_up_ticket_missing` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 6 error(s), 4527 warning(s), 934 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@src/frob/vet/_bare_toolchain.py, DRIFT001@src/frob/gates/__init__.py, DRIFT001@src/frob/gates/_rule_id_scan.py, DRIFT002@src/frob/check/_python.py, SCOPE002@tickets.md
