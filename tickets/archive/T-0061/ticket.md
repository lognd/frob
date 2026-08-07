---
id: T-0061
title: 'strata assert/assume: owner, expiry, verdict report'
state: done
kind: feature
origin: human
created: '2026-07-17'
priority: medium
blocked_by:
- T-0049
parent: T-0050
tier: ticket
sprint: null
scope:
- strata-core/**
- Makefile
- .github/**
- docs/strata/**
- tickets.md
- src/frob/strata/**
- tests/unit/strata/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_report.py::TestCounterexamplePath::test_refuted_line_followed_by_exact_path_line
- tests/unit/strata/test_report.py::TestOrdering::test_refuted_sorts_first_regardless_of_input_order
- tests/unit/strata/test_report.py::TestSummarize::test_all_four_keys_always_present
designated_repro_test: null
threat: null
component: null
---
Assumption ledger (named, owned, expiring; overdue = gate failure); report renders per-claim verdict + quantifier + evidence rung.