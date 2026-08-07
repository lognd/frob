---
id: T-0575
title: 'flake quarantine: per-test stability tracking + quarantine-with-ticket in
  frob test'
state: done
kind: feature
origin: agent
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/testing/**
- docs/modules/testing.md
- tests/unit/testing/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/testing/**
  reason: flake quarantine scope per T-0575 mandate
  actor: logan
  at: '2026-07-22'
- op: add
  glob: docs/modules/testing.md
  reason: flake quarantine scope per T-0575 mandate
  actor: logan
  at: '2026-07-22'
- op: add
  glob: tests/unit/testing/**
  reason: flake quarantine scope per T-0575 mandate
  actor: logan
  at: '2026-07-22'
evidence:
- tests/unit/testing/test_stability.py::TestRecord::test_persists
- tests/unit/testing/test_stability.py::TestRecord::test_window_bounded
- tests/unit/testing/test_stability.py::TestRecord::test_carries_quarantine
- tests/unit/testing/test_stability.py::TestIsFlaky::test_all_pass_ok
- tests/unit/testing/test_stability.py::TestIsFlaky::test_all_fail_ok
- tests/unit/testing/test_stability.py::TestIsFlaky::test_mixed_is_flaky
- tests/unit/testing/test_stability.py::TestIsFlaky::test_single_run_ok
- tests/unit/testing/test_stability.py::TestIsFlaky::test_filters_map
- tests/unit/testing/test_stability.py::TestQuarantine::test_explicit_ticket
- tests/unit/testing/test_stability.py::TestQuarantine::test_rejects_bad
- tests/unit/testing/test_stability.py::TestQuarantine::test_auto_files
- tests/unit/testing/test_stability.py::TestQuarantine::test_lift_clears
- tests/unit/testing/test_stability.py::TestQuarantine::test_lift_unknown_errs
- tests/unit/testing/test_stability.py::TestAlarms::test_closed_still_flaky
- tests/unit/testing/test_stability.py::TestAlarms::test_no_alarm_open
- tests/unit/testing/test_stability.py::TestAlarms::test_no_alarm_stable
- tests/unit/testing/test_stability.py::TestGate::test_already_ok_stays_ok
- tests/unit/testing/test_stability.py::TestGate::test_all_quarantined_ok
- tests/unit/testing/test_stability.py::TestGate::test_one_bad_stays_failed
- tests/unit/testing/test_stability.py::TestCapture::test_empty_ok
- tests/unit/testing/test_stability.py::TestCapture::test_spawn_err
- tests/unit/testing/test_stability.py::TestCapture::test_parses_junit
- tests/unit/testing/test_stability.py::TestTrack::test_captures_then_records
designated_repro_test: null
threat: null
component: null
---
A flaky test blocks every parallel agent. frob test records per-test pass/fail history; a test flipping without related code changes gets flagged, quarantined (excluded from gating) ONLY with an auto-filed ticket, and un-quarantined when stable. Scope: src/frob/testing/, docs/modules/testing.md.