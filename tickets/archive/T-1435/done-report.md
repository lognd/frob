## Done report

Implemented the stamp-time provenance check T-1407 finding 2 called for.
`_provenance_drop` (src/frob/gates/_coverage.py) compares the CURRENT
run's joined module count against the last COMMITTED
frob-coverage.lock.json's own module count -- independent of
`_DEFLATION_FLOOR`'s own self-comparison, which a locally-scoped run
passes trivially (it can join 100% of the few modules it measured).
Wired into `_filtered_coverage_or_deflated` (stamp_coverage's pre-stamp
check) BEFORE the existing sample-size skip, since this check has its
own independent floor (the committed lock's own module count) and must
not be skipped just because today's checkout/known-module count looks
small.

Verified via two new regression tests in tests/test_gates.py's existing
TestCoverageLoad class:
- test_stamp_coverage_refuses_locally_scoped_run_via_provenance_drop:
  ground-truth proof the new check fires where the OLD deflation floor
  alone would not (2-module scoped run, 100% joined, against a 24-module
  committed lock) and that the committed lock is left untouched by the
  refusal.
- test_stamp_coverage_provenance_check_skipped_without_committed_lock:
  no committed lock yet -> stamping proceeds exactly as before this
  ticket.

Full tests/test_gates.py suite (31 TestCoverageLoad tests, 217 total in
the file) still passes: `uv run pytest tests/test_gates.py -p
no:cacheprovider -q` -> all green, no regressions.

docs/guides/agent-playbook.md section 6e updated in the same change to
record that T-1435 closed the gap it had flagged as still-open.

Cut/disclosed: this fixes the STAMP-TIME (`--stamp-coverage`) read path
only, per the ticket's own scope (src/frob/gates/_coverage.py). It does
not change `frob check`'s other, unscoped TEST005 reads elsewhere in
frob.gates (out of this ticket's scope) -- an agent following playbook
section 6b's sanctioned workaround still must not treat a scoped
`pytest --cov` run's coverage.xml as full-run evidence for anything
beyond its own touched set (section 6c already covers this; T-1435 adds
a second, independent line of defense specifically at the point a
scoped run's data gets promoted into the committed lock).

### Changed
```
 Makefile                             |  31 +++++++++-
 docs/guides/agent-playbook.md        |  18 ++++++
 src/frob/gates/_coverage.py          |  76 ++++++++++++++++++++++++
 tests/test_gates.py                  |  90 +++++++++++++++++++++++++++++
 tests/unit/test_makefile_coverage.py |  55 ++++++++++++++++++
 tickets.md                           | 109 +++++++++++++++++++++++++++++++++--
 6 files changed, 373 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestCoverageLoad::test_stamp_coverage_refuses_locally_scoped_run_via_provenance_drop` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCoverageLoad::test_stamp_coverage_provenance_check_skipped_without_committed_lock` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 2 error(s), 874 warning(s), 693 waived
- error-findings: PRE001@tickets/T-1435, SELFAUDIT001@design
