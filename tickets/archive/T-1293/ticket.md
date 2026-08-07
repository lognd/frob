---
id: T-1293
title: 'TEST005 burn-down: src/frob/perf (64 findings, 2 at 0.0%)'
state: done
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: T-1273
tier: ticket
sprint: null
scope:
- src/frob/perf/**
- tests/perf/**
- tests/unit/perf/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/perf/**
  reason: actual perf unit tests live at tests/unit/perf/**, not tests/perf/** as
    originally declared
  actor: logan
  at: '2026-07-31'
evidence:
- tests/unit/perf/test_ratchet.py::TestPersistRoundTrip::test_malformed_json_is_empty_not_a_crash
- tests/unit/perf/test_ratchet.py::TestPersistRoundTrip::test_wrong_schema_json_is_empty_not_a_crash
- tests/unit/perf/test_ratchet.py::TestRatchetViolations::test_findings_become_perf009_violations
- tests/unit/perf/test_harness_sampling.py::TestHarnessSerialPoolsDecision::test_env_unset_installs_serial_pools
designated_repro_test: null
acceptance:
- text: GIVEN the perf package at the 75%/70% floors WHEN frob check --only test runs
    THEN it reports 0 TEST005 findings under src/frob/perf/**
  evidence:
  - tests/unit/perf/test_ratchet.py::TestPersistRoundTrip::test_malformed_json_is_empty_not_a_crash
  - tests/unit/perf/test_ratchet.py::TestPersistRoundTrip::test_wrong_schema_json_is_empty_not_a_crash
- text: GIVEN a 0.0%-branch symbol in perf WHEN it is judged dead code THEN it is
    routed to the DEAD gate/dup machinery or a removal ticket, never given an assert-True
    filler test
  evidence:
  - tests/unit/perf/test_ratchet.py::TestRatchetViolations::test_findings_become_perf009_violations
  - tests/unit/perf/test_harness_sampling.py::TestHarnessSerialPoolsDecision::test_env_unset_installs_serial_pools
- text: GIVEN a new test added to close a perf TEST005 finding WHEN reviewed THEN
    it asserts real behavior (inputs/outputs/side effects), not mere import/instantiation
  evidence:
  - tests/unit/perf/test_ratchet.py::TestPersistRoundTrip::test_malformed_json_is_empty_not_a_crash
  - tests/unit/perf/test_ratchet.py::TestPersistRoundTrip::test_wrong_schema_json_is_empty_not_a_crash
threat: null
component: null
---
Package: src/frob/perf (or the listed root modules).
TEST005 findings at current baseline: 64 total, 2 at exactly
0.0% branch coverage (the priority tier -- dead-code or untested-entry-
point candidates; judge each before writing a test).

0.0%-branch symbols in this package:
_harness.py :: main
_ratchet.py :: ratchet_violations

Work: for each finding, either (a) add a real behavioral test that
exercises the branch/line paths (never assert-True filler, never a test
that only imports the module), or (b) if a 0.0% symbol is confirmed dead
(no live caller, no CLI/API entry point), route it to the DEAD gate / dup
machinery or file a removal ticket instead of writing a fake test for it
-- do not fabricate coverage.