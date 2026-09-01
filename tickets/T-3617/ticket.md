---
id: T-3617
title: tmLanguage missing growth clause keywords (T-3527 regression)
state: in-progress
kind: bug
origin: human
created: '2026-08-31'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- '**/*.tmLanguage.json'
- tests/unit/test_strata_tmlanguage.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/test_strata_tmlanguage.py::test_clause_keywords_covered_by_grammar
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Run 33459475864: tests/unit/test_strata_tmlanguage.py::
test_clause_keywords_covered_by_grammar FAILED on BOTH ubuntu and
macOS -- the only macOS suite failure. T-3527 added the growth clause
('growth PERCENT per PERIOD') to the strata grammar; the tmLanguage
syntax-highlighting grammar was not updated, and the coverage test
correctly caught the drift.

Plan: add the new clause keyword(s) to the tmLanguage file the test
reads (find it via the test's own fixture path) and re-run the test.

Scope: the tmLanguage json + the test file if fixtures need extending.