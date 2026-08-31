---
id: T-3235
title: frob.policy duplicates frob.lang.extract_imports per-language regex
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
- src/frob/policy/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: mark as no-behavior-change refactor for BUG002
  actor: logan
  at: '2026-08-31'
  old_length: 291
  new_length: 639
evidence:
- tests/test_policy.py::TestRules::test_forbidden_import_fires
- tests/test_policy.py::TestRules::test_forbidden_import_passes_outside_glob
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2996 measured frob.policy's per-language import-statement regexes (python/typescript/rust/c/cpp) are a second, parallel implementation of the same axis frob.lang.extract_imports (CAPABILITY_IMPORT_GRAPH) already covers -- a NO-DUPLICATION violation. Measured, not fixed, in T-2996's scope.

frob:no-behavior-change reason="T-3235 replaces the duplicate per-language regex implementation with frob.lang.extract_imports; forbidden-import rule matching semantics (module==specifier or specifier startswith module+.) are preserved, so existing tests that passed before still pass after -- no new failing-then-passing behavior to demonstrate"