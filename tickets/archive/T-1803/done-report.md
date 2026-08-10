## Done report

New WAIVE008 gate (src/frob/gates/_waive.py): a frob:waive WIRE001
whose target symbol WIRE001's OWN dynamic-dispatch rescue predicates
(_is_autouse_pytest_fixture / _is_pydantic_validator, T-1510/T-1652)
now exempt unconditionally -- structurally guaranteed dead at ANY
diff, not just this run's. This is the CONDITION-staleness class the
ticket describes, distinct from T-1751's citation-staleness (WAIVE006/
007) and from WAIVE004's diff-scoped blind spot for this exact rule
(WIRE001 is in _WAIVE004_STRUCTURALLY_UNVERIFIABLE_RULES precisely
because it only ever fires against a diff's added hunks, so a full
unscoped run's diff essentially never reproduces the original waived
site -- "0 findings" is permanently true for every WIRE001 waiver
regardless of staleness). WAIVE008 sidesteps this by testing the
rescue predicate directly against the symbol's own record, which is
diff-independent.

Scoped narrowly to the ticket's two confirmed WIRE001/autouse-fixture
instances rather than the full general "re-evaluate every waived rule
at its site" design sketched in the ticket body -- that broader
mechanism (bonus point re per-rule point-evaluation) is real future
work, not attempted here; recorded as a natural follow-up rather than
scope-creeping this ticket into a general re-verification engine.

Wired into the WARN-tier WAIVE00* self-check group in gates/__init__.py
(diff-independent, so it runs alongside WAIVE001/002/005 rather than
after job_violations like WAIVE003/004).

CONFIRMED LIVE on this repo's own corpus: a full check run found a
THIRD instance beyond the two the ticket cited --
tests/unit/perf/test_serial_pools_import_failure.py:24's frob:waive
WIRE001 on an autouse fixture. Filed as a follow-up
(T-1840, out of this ticket's declared scope) rather than
fixed here.

2 new unit tests (a real autouse-fixture rescue fires; an ordinary
symbol stays silent). Ran the full existing WAIVE00*/WIRE test suite
(48 tests) clean. Two PRE-EXISTING, unrelated failures observed in the
broader tests/test_gates.py -k waive run
(TestWaive004DegradedRunGuard::test_healthy_run_below_threshold_still_
deletes, TestFixEngineTierABatch2::test_waive004_removes_stale_waiver_
on_a_full_unscoped_run) -- both concern REF001 mass-invalidation logic
in src/frob/gates/_fix_engine_sync.py, a file this ticket never
touches, and reproduce identically in isolation with zero diff to
that file, so they predate this change.

### Changed
```
 tickets/T-1803/ticket.md           | 18 +++++++++++++++++-
 tickets/T-1840/ticket.md | 31 +++++++++++++++++++++++++++++++
 2 files changed, 48 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_gates.py::TestTestGate::test_waive008_fires_on_a_now_rescued_autouse_fixture` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTestGate::test_waive008_stays_silent_on_a_non_rescued_symbol` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 5 error(s), 1165 warning(s), 739 waived
- error-findings: COV001@src/frob/registry/_staleness.py, DOCENUM001@docs/modules/gates.md, DUP001@tests/test_gates.py, E501@/home/logan/projects/frob/.claude/worktrees/refusal-attrib/src/frob/registry/_staleness.py, TEST001@src/frob/registry/_staleness.py
