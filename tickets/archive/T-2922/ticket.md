---
id: T-2922
title: 'Unwire the live may= auto-WIDENING Tier-A fixer: capability escalation is
  silently rubber-stamped today'
state: done
kind: security
origin: human
created: '2026-08-25'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_fix_engine_sync.py
- src/frob/gates/_fix_engine.py
- tests/test_gates.py
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_fix_engine_sync.py
  reason: the two live widening call sites and their dispatch-table entries
  actor: logan
  at: '2026-08-25'
- op: add
  glob: src/frob/gates/_fix_engine.py
  reason: unwiring SYS100 auto-widening touches its TIER_A_HANDLERS dispatch entry,
    its own tests, and the doc block describing the deleted fixers
  actor: logan
  at: '2026-08-25'
- op: add
  glob: tests/test_gates.py
  reason: unwiring SYS100 auto-widening touches its TIER_A_HANDLERS dispatch entry,
    its own tests, and the doc block describing the deleted fixers
  actor: logan
  at: '2026-08-25'
- op: add
  glob: docs/modules/gates.md
  reason: unwiring SYS100 auto-widening touches its TIER_A_HANDLERS dispatch entry,
    its own tests, and the doc block describing the deleted fixers
  actor: logan
  at: '2026-08-25'
- op: add
  glob: src/frob/gates/_fix_engine.py
  reason: unwiring SYS100 auto-widening touches its TIER_A_HANDLERS dispatch entry,
    its own tests, and the doc block describing the deleted fixers
  actor: logan
  at: '2026-08-25'
- op: add
  glob: tests/test_gates.py
  reason: unwiring SYS100 auto-widening touches its TIER_A_HANDLERS dispatch entry,
    its own tests, and the doc block describing the deleted fixers
  actor: logan
  at: '2026-08-25'
- op: add
  glob: docs/modules/gates.md
  reason: unwiring SYS100 auto-widening touches its TIER_A_HANDLERS dispatch entry,
    its own tests, and the doc block describing the deleted fixers
  actor: logan
  at: '2026-08-25'
body_changes:
- mode: append
  reason: 'T-4709: preserve SYS100 auto-widening removal history trimmed from _fix_engine_sync.py'
  actor: logan
  at: '2026-09-19'
  old_length: 0
  new_length: 1961
evidence:
- tests/gates_suite/test_fix_engine.py::TestFixEngineTierA::test_sys100_core_violation_still_fires_and_is_not_auto_resolved
- tests/gates_suite/test_fix_engine.py::TestFixEngineTierA::test_sys100_extended_violation_still_fires_and_is_not_auto_resolved
- tests/gates_suite/test_fix_engine.py::TestFixEngineTierABatch2::test_tier_a_handlers_dict_covers_every_batch_rule
designated_repro_test: tests/gates_suite/test_fix_engine.py::TestFixEngineTierA::test_sys100_core_violation_still_fires_and_is_not_auto_resolved
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 79796984784859d6c6bb3d235ddb2194bcb8c9dc
---

T-4709 follow-up (condensed from the SYS100-auto-widening-removal comment
block in src/frob/gates/_fix_engine_sync.py, trimmed for DOCARCH002's
12-line cap):

Two handlers used to live at this spot: `fix_sys100_may_via_union`
(T-1531 CORE, per-file `via`-list widening) and
`fix_sys100_extended_whole_node_grant` (T-1545 EXTENDED, whole-node
grant insertion for eval/process-control/ffi/... kinds with no per-file
evidence to narrow to). Both did the same wrong thing: when frob's own
SYS100 self-conformance check observed a file exercising a capability
its node's `may=` declaration did not grant, they edited the
DECLARATION to grant it -- the ceiling became a restatement of behavior,
never a constraint on it.

T-1623/T-1628 put this auto-widening in place as a deliberate, accepted
policy at the time (T-1531's/T-1545's own docstrings, now deleted along
with them, said so explicitly). T-2922/T-2920 SUPERSEDE that decision on
the user's explicit instruction, removing the one live code path that
violated the shrink-only rework going forward.

The SYS111 capability-via-ratchet-lock sync just below this comment
(`fix_sys111_capability_ratchet_sync`, T-2001) was itself built BECAUSE
of this widening's failure mode (T-1977/T-1665: a SYS100 auto-widening
would satisfy SYS100/SYS104 while leaving the ratchet lock's committed
ceiling stale) -- it is UNAFFECTED by this removal beyond becoming a
structural no-op wherever its own growth-attribution finds nothing new
to bump, since SYS100 no longer produces any growth for it to sync.

`frob.strata._sync_may`'s `apply_sync_may`/`sync_may_report`/
`apply_sync_may_extended`/`sync_may_extended_report`/
`WholeNodeMayGrantDiff` writer functions these two handlers called are
DELETED (T-2920, once this ticket's own land confirmed zero remaining
importers) -- `src/frob/strata/_sync_may.py` now holds only the shared
`.strata` body-span scanner (`node_body_span`) `frob.strata._shrink`
(T-2923) still uses.