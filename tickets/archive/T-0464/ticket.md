---
id: T-0464
title: make coverage must enable subprocess coverage (COVERAGE_PROCESS_START) -- without
  it coverage.xml is deflated 0.49 vs real 0.87, exploding TEST005 to 507 false findings;
  + coverage.xml staleness/freshness check (source_sha is the xml's own sha, not the
  measured source)
state: done
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- Makefile
- src/frob/gates/
- src/frob/gates/_coverage.py
- pyproject.toml
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestTestGate::test_test011_fires_on_stale_mtime
- tests/test_gates.py::TestTestGate::test_test011_silent_when_fresh_and_fully_joined
- tests/test_gates.py::TestCoverageLoad::test_load_coverage_flags_stale_by_mtime
designated_repro_test: null
threat: null
component: null
---
