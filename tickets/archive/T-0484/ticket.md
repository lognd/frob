---
id: T-0484
title: 'coverage cycle is too slow to run per-change: incrementalize / background
  it (daemon-side), so TEST005/TEST006 feedback is not a full-suite wait'
state: done
kind: feature
origin: human
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/testing/
- src/frob/gates/_coverage.py
- tests/test_coverage.py
- Makefile
- docs/modules/testing.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_coverage.py
  reason: T-0484 needs a regression test (mirrored path per repo convention, tests/
    dir has no src/frob/testing/ mirror glob in scope) and the Makefile coverage target
    is the concrete incrementalization deliverable named in the mission/ticket body
  actor: logan
  at: '2026-07-21'
- op: add
  glob: Makefile
  reason: T-0484 needs a regression test (mirrored path per repo convention, tests/
    dir has no src/frob/testing/ mirror glob in scope) and the Makefile coverage target
    is the concrete incrementalization deliverable named in the mission/ticket body
  actor: logan
  at: '2026-07-21'
- op: add
  glob: docs/modules/testing.md
  reason: new public symbol python_coverage_targets needs a frob:doc/describes anchor
    (COV001/DOC002)
  actor: logan
  at: '2026-07-21'
evidence:
- tests/test_coverage.py::TestPythonCoverageTargets::test_touched_source_selects_test
- tests/test_coverage.py::TestPythonCoverageTargets::test_nothing_touched_returns_empty
- tests/test_coverage.py::TestPythonCoverageTargets::test_bad_base_ref_returns_empty
designated_repro_test: null
threat: null
component: null
---
make coverage runs the whole suite under coverage on every change, so the stale-stamp gate (TEST006) forces a full re-run for a one-line edit. Explore: (a) daemon-side background coverage refresh on file-change, (b) per-file/touched-set incremental coverage merged into the stamp, (c) caching unchanged modules' coverage. Goal: TEST005/TEST006 feedback in seconds, not a full suite.