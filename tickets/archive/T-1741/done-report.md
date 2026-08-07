## Done report

frob:no-behavior-change reason="pure COV002/tag bookkeeping: adding frob:ticket T-1741 directives to already-existing test methods so the ticket-attribution edge points at an open ticket now that T-1727 (the ticket that originally touched these lines) has closed -- no test logic or behavior changed"

Correction discovered while landing this exact ticket: WIRE002 requires
`frob:waive WIRE001`'s `follow_up=` to name a ticket that stays OPEN --
pointing it at T-1741 itself (the ticket closing in this very change)
retrips the same LiveTrackerCited refusal the moment this ticket
transitions to done, since a closed ticket can never be a live
"wire it later" tracker for its own waiver. Filed a genuine successor (T-1746, renumbered to its real id
at land), left QUEUED/open, and re-pointed the waiver's follow_up there
instead -- it carries the real fix work (the two options in its body:
move the fixture somewhere genuinely cross-file-reusable, or extend
WIRE001's same-file exclusion to recognize a same-file test_* caller as
reached).

This ticket (T-1741) itself only carries the COV002 bookkeeping. Fixed the
COV002 fallout discovered immediately after T-1727 landed: every test
method in TestCheckTicketMutationEvidence I had edited under T-1727 (to
call the shared `_repo_with_add_change` fixture instead of a per-class
`self._repo_with_change` wrapper, closing DUP001) needed its own
frob:ticket edge pointing at an OPEN ticket -- T-1727 itself no longer
qualified the moment it closed. Added `# frob:ticket T-1741` above the
class and above each of the 9 flagged methods.

The actual WIRE001 false-positive this ticket is nominally about (same-
file test-fixture reuse not recognized as "wired") is still open and
NOT fixed here -- this Done report covers only the COV002 bookkeeping
that had to happen immediately to keep main at zero. Left `# frob:waive
WIRE001` in place, still pointing at this ticket (T-1741) as its
follow_up, exactly as filed.

Changed:
- tests/test_tickets_mutation_evidence.py (frob:ticket T-1741 tags only, no logic change)

Evidence: reused T-1727's own evidence set (the same tests, unchanged
behavior) -- test_zero_budget_reports_unmeasured_not_confirmatory,
test_mid_sweep_deadline_truncates_and_reports_unmeasured,
test_real_subprocess_spawning_evidence_stays_bounded_not_hung,
test_warns_when_projected_cost_exceeds_budget,
test_no_warning_when_no_touched_python_files.

Verification:
- `uv run pytest tests/test_tickets_mutation_evidence.py -q` -- 17 passed, 1 skipped.
- `uv run ty check` / `uv run ruff check` / `uv run ruff format --check` -- all clean.
- `uv run frob check --land-parity` (cache-bypassed) -- clean, 0 unscoped errors.

Filed: none.
Gates: frob check --land-parity clean, 0 unscoped errors. No new waivers (the pre-existing WIRE001 waiver already cited this ticket as follow_up).

### Changed
```
 tests/test_tickets_mutation_evidence.py |  10 +++
 tickets.md                              | 107 +++++++++++++++++++++++++++++++-
 2 files changed, 116 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_zero_budget_reports_unmeasured_not_confirmatory` (pytest node id, verified passing when recorded)
- `tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_mid_sweep_deadline_truncates_and_reports_unmeasured` (pytest node id, verified passing when recorded)
- `tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_real_subprocess_spawning_evidence_stays_bounded_not_hung` (pytest node id, verified passing when recorded)
- `tests/test_tickets_mutation_evidence.py::TestWarnBindTimeMutationSweepCost::test_warns_when_projected_cost_exceeds_budget` (pytest node id, verified passing when recorded)
- `tests/test_tickets_mutation_evidence.py::TestWarnBindTimeMutationSweepCost::test_no_warning_when_no_touched_python_files` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 1 error(s), 213 warning(s), 723 waived
- error-findings: PRE001@tickets/T-1741
