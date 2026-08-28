---
id: T-3255
title: Fix malformed directive false-positive in docarch001_violations wiring comment
state: done
kind: bug
origin: human
created: '2026-08-28'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/__init__.py
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_gates.py
  reason: regression test proving no malformed-directive false positive on the real
    gates/__init__.py file after the reword
  actor: logan
  at: '2026-08-28'
evidence:
- tests/test_gates.py::TestDsl001::test_docarch001_wiring_comment_does_not_self_match
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 2282f6de7700fa068c79f401c55764a2e17c8503
---
T-2988 landed a comment near the docarch001_violations call site in run_gates that reads 'applied to public docstrings instead of frob:waive reasons' -- the literal token 'frob:waive' mid-prose gets picked up by frob.graph.dsl's directive scanner and fails to parse as a real directive (bad attribute syntax), surfacing as a DSL001-eligible malformed directive at src/frob/gates/__init__.py:8399 (confirmed via land's own WARNING: malformed directive log line). Reword the comment to avoid the literal 'frob:waive ' token outside an actual directive (e.g. 'a waive-style reason' or backtick/hyphenate it so the scanner does not match).