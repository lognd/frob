---
id: T-0874
title: 'stale-waiver purge: delete full-run WAIVE004 zero-match waivers, gate:WAIVE
  to zero (562 baseline)'
state: done
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: T-0204
tier: ticket
sprint: null
scope:
- src/frob/**
- tests/**
- frob.toml
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_stats_agentic.py::test_retread_candidates_require_repeat_and_known_tree_hash
- tests/test_gates.py::TestCoverageGate::test_waiver_suppresses_and_reports
designated_repro_test: null
acceptance:
- text: GIVEN a full frob check after the purge WHEN gate:WAIVE evaluates THEN it
    reports zero warnings, and no previously-masked ERROR was introduced (any resurfaced
    finding is fixed or re-waived with a current reason)
  evidence:
  - tests/test_gates.py::TestCoverageGate::test_waiver_suppresses_and_reports
threat: null
component: gates
---
T-0204 child (waive family). gate:WAIVE reports 562 warnings at 2026-07-23 baseline, dominated by WAIVE004 "waiver matches 0 findings this run" from a FULL check (authoritative, unlike scoped-run WAIVE004 flakes -- see T-0846/T-0850 history). A waiver matching nothing in a full run is stale: the underlying finding was fixed or the rule changed. Sweep: for each WAIVE004 in a full run, delete the waiver; where deletion resurfaces a real finding, that finding is the honest state (fix or re-waive with a current reason). Also triage any WAIVE003-class aging warnings. MUST be run against a full (not scoped) check and re-verified with a second full run after the purge. Deliverable: gate:WAIVE 0 warnings.