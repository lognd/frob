---
id: T-3465
title: 'SELFAUDIT001: testsuite node undeclared fs.write/exec (test_strata_core_gil.py)
  and env.read (test_worker.py)'
state: in-progress
kind: bug
origin: human
created: '2026-08-30'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- design/frob.strata
- docs/design/registry/capability-via-ratchet.lock.json
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/design/registry/capability-via-ratchet.lock.json
  reason: SYS111 ratchet ceiling bump required by the new via-list entries this ticket
    adds
  actor: logan
  at: '2026-08-30'
body_changes:
- mode: append
  reason: widen to cover every currently undeclared capability site per coordinator
    instruction, not just the two originally-filed test files
  actor: logan
  at: '2026-08-30'
  old_length: 993
  new_length: 1988
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
found while working T-3449 (post T-3458 re-measurement).

After T-3458's fix (compiled glob cache for _via_matches), the T-3449 5-test bundle under -n 4 runs clean in 176s with zero worker crashes (was: >308s with gw3/gw4 crashes before T-3458). No further T-3449 stall/crash fix is needed.

But test_sys_gate_zero_violations now fails with 8 real SELFAUDIT001 violations against the live repo, all pre-existing and unrelated to T-3449's scope:
  - tests/unit/strata/test_strata_core_gil.py:50 capability fs.write not declared (test file added by T-3457's GIL fix)
  - tests/unit/strata/test_strata_core_gil.py:67 capability exec not declared
  - tests/unit/verify/test_worker.py:302,303,345,348,377,378 capability env.read not declared (6 sites)

These need testsuite node via-list / effect declarations added in design/frob.strata for the affected files/capabilities. Out of scope for T-3449 (whose scope is src/frob/strata/_selfconform*.py, _claims.py, _facts.py -- not design/frob.strata).

Widened per coordinator (2026-08-30): CI run 33298117154 (HEAD f821615ca) showed 5/8 ubuntu failures on this same SYS100 class, including src/frob/gates/_policy_weakening_gate.py:108 (fs.read, T-3460) not in the original filing. Re-measured on current main (this worktree): 29 SELFAUDIT001/SYS100 violations total across 2 nodes:

node=gates (5): src/frob/gates/_land_parity.py:203,374 fs.read; src/frob/gates/_land_parity.py:329,334 fs.write; src/frob/gates/_policy_weakening_gate.py:108 fs.read.

node=testsuite (24): tests/unit/strata/test_strata_core_gil.py:50 fs.write, :67 exec; tests/unit/test_land_parity_gate.py:25,26 exec, :57,75,90,123,146,151 fs.write (7 sites); tests/unit/test_sync_claude_config_stale_guard_t3408.py:106 env.read, :132,189 fs.read (2 sites), :132,133,136,145,152 fs.write (5 sites); tests/unit/verify/test_worker.py:399,400,442,445,474,475 env.read (6 sites).

This ticket now covers EVERY currently undeclared SYS100 site above, not just the original two files.