---
id: T-1298
title: 'TEST005 burn-down: src/frob/stats (13 findings, 0 at 0.0%)'
state: done
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: T-1273
tier: ticket
sprint: null
scope:
- src/frob/stats/**
- tests/stats/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_stats.py::test_ticket_stats_counts_states_and_doable
- tests/test_stats_agentic.py::test_category_time_buckets_by_subcommand
- tests/test_stats_agentic.py::test_retread_candidates_require_repeat_and_known_tree_hash
designated_repro_test: null
acceptance:
- text: GIVEN the stats package at the 75%/70% floors WHEN frob check --only test
    runs THEN it reports 0 TEST005 findings under src/frob/stats/**
  evidence:
  - tests/test_stats.py::test_ticket_stats_counts_states_and_doable
  - tests/test_stats_agentic.py::test_category_time_buckets_by_subcommand
  - tests/test_stats_agentic.py::test_retread_candidates_require_repeat_and_known_tree_hash
- text: GIVEN a 0.0%-branch symbol in stats WHEN it is judged dead code THEN it is
    routed to the DEAD gate/dup machinery or a removal ticket, never given an assert-True
    filler test
  evidence:
  - tests/test_stats.py::test_ticket_stats_counts_states_and_doable
- text: GIVEN a new test added to close a stats TEST005 finding WHEN reviewed THEN
    it asserts real behavior (inputs/outputs/side effects), not mere import/instantiation
  evidence:
  - tests/test_stats.py::test_ticket_stats_counts_states_and_doable
  - tests/test_stats_agentic.py::test_category_time_buckets_by_subcommand
  - tests/test_stats_agentic.py::test_retread_candidates_require_repeat_and_known_tree_hash
threat: null
component: null
---
Package: src/frob/stats (or the listed root modules).
TEST005 findings at current baseline: 13 total, 0 at exactly
0.0% branch coverage (the priority tier -- dead-code or untested-entry-
point candidates; judge each before writing a test).

0.0%-branch symbols in this package:
(none at exactly 0.0% -- all findings are partial-coverage or module-line)

Work: for each finding, either (a) add a real behavioral test that
exercises the branch/line paths (never assert-True filler, never a test
that only imports the module), or (b) if a 0.0% symbol is confirmed dead
(no live caller, no CLI/API entry point), route it to the DEAD gate / dup
machinery or file a removal ticket instead of writing a fake test for it
-- do not fabricate coverage.