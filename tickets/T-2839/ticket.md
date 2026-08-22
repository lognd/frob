---
id: T-2839
title: Fix malformed frob:waive LARGE001 directive on arch/_patterns.py (T-2823 regression)
state: done
kind: bug
origin: human
created: '2026-08-21'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/arch/_patterns.py
evidence_scope:
- tests/test_arch_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'BUG002 waiver: comment-text fix, no code logic changed, existing parser
    test coverage applies'
  actor: logan
  at: '2026-08-21'
  old_length: 505
  new_length: 988
evidence:
- tests/test_arch_gate.py::TestArchGateLargeFile::test_large_file_fires_large001_warn
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2823 added a frob:waive LARGE001 comment to src/frob/arch/_patterns.py whose reason text contains an escaped quote (severity backslash-quote suggestion backslash-quote) that the frob:<verb> comment-DSL attribute grammar cannot parse, producing a 'malformed directive: bad attribute syntax' warning on every frob check run since. Rewrite the reason text without embedded quotes so the directive parses cleanly, and confirm frob check --only static/arch no longer reports this malformed-directive warning.

<!-- frob:waive BUG002 reason="the defect is a comment-text typo (an embedded escaped double-quote inside a frob:waive reason string) in a single file, not a code-logic defect; the generic malformed-directive parser this bug tripped is already covered by tests/unit/graph/test_dsl.py's own malformed-directive test suite, and a bespoke repro-at-parent test for one specific comment string in one file would not exercise anything the existing parser tests do not already cover" -->