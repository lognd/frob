---
id: T-1435
title: Add a stamp-time provenance check for a locally-scoped coverage.xml misread
  as a full run (T-1407 finding 2)
state: done
kind: bug
origin: human
created: '2026-08-02'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_coverage.py
- docs/guides/agent-playbook.md
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_gates.py
  reason: 'The stamp-time provenance check this ticket implements needs regression

    tests to satisfy the evidence/test-coverage discipline (section 5/6 of

    docs/guides/agent-playbook.md): a new refusal path in

    src/frob/gates/_coverage.py with no test exercising it is unverified

    behavior, not done work. tests/test_gates.py is the existing home for

    every other _coverage.py regression test (TestCoverageLoad class) --

    adding a parallel test file would duplicate its fixtures/helpers. Adding

    this single file to scope keeps the new tests colocated with the tests

    they extend.

    '
  actor: logan
  at: '2026-08-02'
evidence:
- tests/test_gates.py::TestCoverageLoad::test_stamp_coverage_refuses_locally_scoped_run_via_provenance_drop
- tests/test_gates.py::TestCoverageLoad::test_stamp_coverage_provenance_check_skipped_without_committed_lock
designated_repro_test: null
threat: null
component: null
---
T-1407 investigated why coverage.xml consistently only ever joined ~53% of
known modules even from a full, healthy make coverage run. Direct
measurement (T-1406, this same dispatch) found the root cause was NOT a
measurement/instrumentation gap at all: module_join_fraction's denominator
(_known_repo_paths) counted every .py file in the whole repo -- tests/**,
scripts, everything -- even though make coverage runs pytest --cov=src/frob,
which can structurally never report on anything outside that root. 447 real
src/frob modules / 851 repo-wide known modules = 0.53, a purely structural
artifact of an unscoped denominator, not evidence of any run ever dropping
real data. T-1406 fixed the denominator to scope against coverage.xml's own
<sources> declaration; once landed, a healthy run's module_join_fraction
should read close to 1.0, not ~0.53.

What T-1406 does NOT address, and what remains a live risk: T-1407's second
finding -- burn-down agents' own scoped pytest --cov runs (the sanctioned
section 6b workaround for the make-coverage-is-coordinator-only rule) leave
a narrow coverage.xml on disk that a LATER, unscoped frob check can silently
misread as if it were the full run's data. There is currently no mechanism
that tells these two situations apart at read time.

T-1407's own brief suggested the concrete fix: "a stamp-time provenance
check (e.g. refuse/warn a frob check TEST005 read against a coverage.xml
whose recorded module count is far below the last committed lock's)."
Implement that: at TEST005/--stamp-coverage read time, compare the current
coverage.xml's module count (or module_join_fraction, now that T-1406 makes
that number mean something real) against the last COMMITTED
frob-coverage.lock.json's own module count/fraction; a large, otherwise
unexplained drop is the exact fingerprint of "a narrower, locally-scoped
coverage.xml is on disk, not a full run's" and should warn (or, if the gap
is severe enough, refuse) rather than silently evaluate TEST005 against it.

This must build on T-1406 (module_join_fraction has to mean something
trustworthy first) and should re-verify T-1406's fix has actually landed
and been observed against a real make coverage run before calibrating any
threshold, per this ticket's own investigation discipline.