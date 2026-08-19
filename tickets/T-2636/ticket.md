---
id: T-2636
title: tmLanguage grammar missing 'exclusive' clause keyword (test red on main)
state: queued
kind: bug
origin: human
created: '2026-08-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
scope:
- tests/unit/test_strata_tmlanguage.py
- editors/vscode-strata/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Filed from T-2623's tests/unit/ red-test sweep (measured at main sha
5a15dbd92, 18 red of 5237 collected).

tests/unit/test_strata_tmlanguage.py::test_clause_keywords_covered_by_grammar
fails: "parser clause keywords missing from tmLanguage clause-keywords:
['exclusive']" -- the strata parser recognizes an `exclusive` clause
keyword (via at_keyword/expect_keyword call sites) that the VS Code syntax
grammar (editors/vscode-strata's tmLanguage json, per src/frob/deploy/
_drift.py's tmLanguage reference) does not highlight. This is a real,
one-directional gap: add 'exclusive' to the grammar's clause-keywords
pattern. Low risk, single-keyword addition -- do not touch the parser side,
this test is deliberately one-directional (parser -> grammar only).

Not fixed in T-2623 due to a time-boxed land window (T-2611 draining the
fleet for a repo-wide renormalization land).
