---
id: T-0626
title: 'arch: register all ARCH1xx checks in the T-0343 unified registry, close the
  DENOMINATOR MANIFEST gap for T-0330'
state: done
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0616
- T-0617
- T-0618
- T-0619
- T-0620
- T-0621
- T-0622
- T-0623
- T-0624
- T-0625
parent: T-0330
tier: ticket
sprint: null
scope:
- docs/design/registry/**
- docs/design/architecture-check-catalog.md
- docs/design/design-pattern-traps-corpus.md
- tests/test_registry_exhaustiveness.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_registry_exhaustiveness.py
  reason: T-0626 docs-only registry-disposition edits verified by this file's existing
    registry_gate classification-path tests -- same convention as T-0330's own scope_changes
    (test file mirrors the doc-only scope, T-0455 hygiene precedent)
  actor: logan
  at: '2026-07-26'
evidence:
- tests/test_registry_exhaustiveness.py::TestDisposition::test_dangling_handled_by_fails
- tests/test_registry_exhaustiveness.py::TestDisposition::test_handled_by_real_rule_passes
- tests/test_registry_exhaustiveness.py::TestEnforcesConformance::test_handled_by_with_no_frob_enforces_edge_warns
- tests/test_registry_exhaustiveness.py::TestOutOfScopeCaughtBy::test_substantive_reasoned_none_is_silent
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
threat: null
component: null
---
Per T-0330's EXHAUSTIVENESS DRIFT-LOCK paragraph: every tier-1 statically-checkable entry in architecture-check-catalog.md and every trap hallmark in design-pattern-traps-corpus.md that this epic's ARCH1xx family (T-0616..T-0625) was meant to cover must get a disposition in docs/design/registry/ (addressed-by-check <ARCHxxx id> | reasoned-deferral | duplicate-of | out-of-scope), per the T-0343 REG001 gate contract. Acceptance: frob check's registry gate (REG001-family) shows zero unaccounted entries whose owning corpus row maps to T-0330's scope; any entry NOT built in T-0616..T-0625 gets an explicit reasoned-deferral or out-of-scope disposition, never silently dropped. This ticket is the epic's actual close condition -- T-0330 cannot close until this is green.