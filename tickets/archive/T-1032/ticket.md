---
id: T-1032
title: 'fix stale test_every_deferred_entry_targets_an_open_ticket: system-design.yaml
  has 0 deferred entries now (T-0958 resolved them)'
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/test_registry_reconciliation_system_design.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_registry_reconciliation_system_design.py::TestSystemDesignExhaustiveness::test_every_deferred_entry_targets_an_open_ticket
designated_repro_test: null
threat: null
component: null
---
Found while working T-0658: `tests/test_registry_reconciliation_system_design.py::TestSystemDesignExhaustiveness::test_every_deferred_entry_targets_an_open_ticket` fails on a fresh worktree built from current main, unrelated to T-0658's own scope (docs/design/registry/system-design.yaml is a different scope than this test file, and neither was touched to cause this).

Root cause: the test asserts `deferred` (entries with `disposition.kind is DispositionKind.DEFERRED`) is non-empty in the live `docs/design/registry/system-design.yaml`. At the time T-0392 wrote this test, ~105 genuine entries were deferred to T-0331/a re-pointed successor. Since then, T-0958 (per system-design.yaml's own header comment) re-dispositioned all of them into `handled_by:RULE` (21 entries) or `out_of_scope:...` (97 entries) or `duplicate-of-artifact` (1 entry) -- the live file now has ZERO `deferred:` dispositions (verified directly: `frob.registry.audit_registry_file` reports `deferred=0`, `handled=21`, `out_of_scope=97`, `duplicate=1`, `unaccounted=0`, `exhausted=True`). The test's "expected at least one deferred entry to check against" assumption no longer holds -- not a regression in the registry file (it is MORE fully dispositioned now, a good outcome), but a stale assumption baked into the test itself.

Fix: either loosen the assertion to `if deferred:` (skip cleanly when zero, matching the file's now-fully-resolved state) or remove/replace the test with one that positively asserts the CURRENT resolved state, whichever the reviewer judges is the more honest signal for future drift. Scope: tests/test_registry_reconciliation_system_design.py only -- the registry file itself needs no change (it is honestly, fully dispositioned already).