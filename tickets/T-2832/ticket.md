---
id: T-2832
title: 'REG008 burn-down batch 2/N: 17 missing frob:enforces directives across gates/app/strata/check
  modules'
state: done
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
- src/frob/app/_check_chunking.py
- src/frob/app/check_runner.py
- src/frob/check/__init__.py
- src/frob/check/_python.py
- src/frob/deploy/_conform.py
- src/frob/gates/_exhaustive_handling.py
- src/frob/gates/_registry_exhaustiveness.py
- src/frob/gates/_sys_selfaudit.py
- src/frob/strata/_capacity.py
- src/frob/strata/_cve_fingerprint.py
- src/frob/strata/_selfconform.py
- tests/test_registry_exhaustiveness.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/app/_check_chunking.py
  reason: 'REG008 burn-down batch 2/N: add missing frob:enforces directive at each
    entry''s real violation-emitting function'
  actor: logan
  at: '2026-08-21'
- op: add
  glob: src/frob/app/check_runner.py
  reason: 'REG008 burn-down batch 2/N: add missing frob:enforces directive at each
    entry''s real violation-emitting function'
  actor: logan
  at: '2026-08-21'
- op: add
  glob: src/frob/check/__init__.py
  reason: 'REG008 burn-down batch 2/N: add missing frob:enforces directive at each
    entry''s real violation-emitting function'
  actor: logan
  at: '2026-08-21'
- op: add
  glob: src/frob/check/_python.py
  reason: 'REG008 burn-down batch 2/N: add missing frob:enforces directive at each
    entry''s real violation-emitting function'
  actor: logan
  at: '2026-08-21'
- op: add
  glob: src/frob/deploy/_conform.py
  reason: 'REG008 burn-down batch 2/N: add missing frob:enforces directive at each
    entry''s real violation-emitting function'
  actor: logan
  at: '2026-08-21'
- op: add
  glob: src/frob/gates/_exhaustive_handling.py
  reason: 'REG008 burn-down batch 2/N: add missing frob:enforces directive at each
    entry''s real violation-emitting function'
  actor: logan
  at: '2026-08-21'
- op: add
  glob: src/frob/gates/_registry_exhaustiveness.py
  reason: 'REG008 burn-down batch 2/N: add missing frob:enforces directive at each
    entry''s real violation-emitting function'
  actor: logan
  at: '2026-08-21'
- op: add
  glob: src/frob/gates/_sys_selfaudit.py
  reason: 'REG008 burn-down batch 2/N: add missing frob:enforces directive at each
    entry''s real violation-emitting function'
  actor: logan
  at: '2026-08-21'
- op: add
  glob: src/frob/strata/_capacity.py
  reason: 'REG008 burn-down batch 2/N: add missing frob:enforces directive at each
    entry''s real violation-emitting function'
  actor: logan
  at: '2026-08-21'
- op: add
  glob: src/frob/strata/_cve_fingerprint.py
  reason: 'REG008 burn-down batch 2/N: add missing frob:enforces directive at each
    entry''s real violation-emitting function'
  actor: logan
  at: '2026-08-21'
- op: add
  glob: src/frob/strata/_selfconform.py
  reason: 'REG008 burn-down batch 2/N: add missing frob:enforces directive at each
    entry''s real violation-emitting function'
  actor: logan
  at: '2026-08-21'
- op: add
  glob: tests/test_registry_exhaustiveness.py
  reason: 'REG008 burn-down batch 2/N: add missing frob:enforces directive at each
    entry''s real violation-emitting function'
  actor: logan
  at: '2026-08-21'
body_changes:
- mode: append
  reason: declare no-behavior-change per BUG002's remedy option 2 -- comment-only
    diff
  actor: logan
  at: '2026-08-21'
  old_length: 1585
  new_length: 1893
evidence:
- tests/test_registry_exhaustiveness.py::TestEnforcesConformance::test_handled_by_with_frob_enforces_edge_is_silent
designated_repro_test: null
acceptance:
- text: given the 17 fixed registry entries, when frob check --json runs, then those
    entries no longer appear as REG008 findings
  evidence:
  - tests/test_registry_exhaustiveness.py::TestEnforcesConformance::test_handled_by_with_frob_enforces_edge_is_silent
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Batch 2/N of T-2369. T-2812 (batch 1) fixed 18/36 REG008 findings. Full unbudgeted re-measurement (frob check --json, gate-summary present) confirmed 18 remaining, exactly matching T-2812's disclosed 'remaining' list. Characterization: one homogeneous class (a registry entry dispositioned handled_by:<RULE> with no matching # frob:enforces <ENTRY-ID> directive anywhere in code) but genuinely scattered across 9 files with no shared root cause -- unlike REF001's glob-entrypoint collapse, no single structural fix applies here since each rule's real violation-emitting function is a distinct symbol. This batch fixes 17 of the 18: SLH-SYS-EVA-03-UNDECLARED-PUBLIC-SURFACE, CHK-GATE-SYS108, CHK-GATE-SYS109, CHK-GATE-SYS110, CHK-GATE-SYS112, CHK-GATE-BUDGET001, CHK-GATE-CHECK001, CHK-GATE-CVEFP001, CHK-GATE-DEPLOY001, CHK-GATE-DEPLOY002, CHK-GATE-DEPLOY003, CHK-GATE-DERIVED001, CHK-GATE-CAP001, CHK-GATE-CLAUDE001, CHK-GATE-EXHAUST004, CHK-GATE-CYCLE001, CHK-GATE-QUEUE001 -- each got a # frob:enforces directive added directly above its real violation-emitting function. The 18th, CHK-GATE-DOC012 (src/frob/gates/_docblocks.py), is EXCLUDED from this batch: that file is held by a live in-progress lease from T-2359 (a stalled reformat-batch ticket with no active worktree), so a scope --add there is refused (ScopeLeaseConflict). REG008 is NOT promoted WARN->ERROR in this batch -- 1 finding remains, and promoting early would red main for that one unfixed entry. Re-measured full unbudgeted frob check --json after this batch's fix: REG008 = 1 (CHK-GATE-DOC012 only), still WARN.

frob:no-behavior-change reason="adds 17 missing frob:enforces comment directives above existing violation-emitting functions in gates/app/strata/check modules; each function's runtime behavior, return values, and existing tests are unchanged -- this is metadata linking code to registry entries, not logic"