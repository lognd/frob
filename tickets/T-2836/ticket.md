---
id: T-2836
title: 'REG008 burn-down batch 3/N: CHK-GATE-DOC012 (final entry, lease cleared)'
state: queued
kind: bug
origin: agent
created: '2026-08-21'
priority: medium
parent: T-2369
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_docblocks.py
- src/frob/gates/_registry_exhaustiveness.py
- tests/test_registry_exhaustiveness.py
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_docblocks.py
  reason: 'batch 3/N: add missing frob:enforces CHK-GATE-DOC012 directive; document
    REG008''s remaining count'
  actor: logan
  at: '2026-08-21'
- op: add
  glob: src/frob/gates/_registry_exhaustiveness.py
  reason: 'batch 3/N: add missing frob:enforces CHK-GATE-DOC012 directive; document
    REG008''s remaining count'
  actor: logan
  at: '2026-08-21'
- op: add
  glob: tests/test_registry_exhaustiveness.py
  reason: 'batch 3/N: add missing frob:enforces CHK-GATE-DOC012 directive; document
    REG008''s remaining count'
  actor: logan
  at: '2026-08-21'
- op: add
  glob: docs/modules/gates.md
  reason: 'batch 3/N: add missing frob:enforces CHK-GATE-DOC012 directive; document
    REG008''s remaining count'
  actor: logan
  at: '2026-08-21'
designated_repro_test: null
acceptance:
- text: given CHK-GATE-DOC012, when frob check --json runs, then it no longer appears
    as a REG008 finding
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Batch 3/N of T-2369. T-2812 (batch 1, 36->18) and T-2832 (batch 2, 18->1, excluding CHK-GATE-DOC012 which was blocked by T-2359's live lease on src/frob/gates/_docblocks.py) left exactly one entry: CHK-GATE-DOC012. The coordinator released T-2359's leaked lease; this batch adds the missing # frob:enforces CHK-GATE-DOC012 directive above doc012_gate in src/frob/gates/_docblocks.py. Full unbudgeted re-measurement after this fix shows REG008 = 3, not 0 -- the 3 remaining entries (CHK-GATE-SYS108, CHK-GATE-SYS110, SLH-SYS-EVA-03-UNDECLARED-PUBLIC-SURFACE) all site in src/frob/strata/_selfconform.py, which T-2729 (queued: split that file by SYS1xx rule family) declares in its own scope; adding directives there triggered CrossTicketLeakage at land time in the prior batch and was reverted. REG008 severity stays WARN in this batch -- not yet a true zero.