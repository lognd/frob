---
id: T-2379
title: Burn frob-arch WARN findings (god-class/god-module/lock-order/etc) to zero,
  then promote to error
state: done
kind: bug
origin: agent
created: '2026-08-17'
priority: medium
parent: T-0969
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/serve/_daemon.py
- src/frob/vet/_capability_core.py
- src/frob/gates/_pii_structural/_keywords.py
- tickets/T-3494/**
- src/frob/arch/_shared_state_race.py
- src/frob/arch/_lock_ordering.py
- src/frob/check/_python.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/serve/_daemon.py
  reason: 'T-2379 frob-arch burn-down: unguarded-shared-write x2 (daemon.py), lock-order-cycle
    (capability_core.py), type-dispatch-smell (keywords.py)'
  actor: logan
  at: '2026-08-30'
- op: add
  glob: src/frob/vet/_capability_core.py
  reason: 'T-2379 frob-arch burn-down: unguarded-shared-write x2 (daemon.py), lock-order-cycle
    (capability_core.py), type-dispatch-smell (keywords.py)'
  actor: logan
  at: '2026-08-30'
- op: add
  glob: src/frob/gates/_pii_structural/_keywords.py
  reason: 'T-2379 frob-arch burn-down: unguarded-shared-write x2 (daemon.py), lock-order-cycle
    (capability_core.py), type-dispatch-smell (keywords.py)'
  actor: logan
  at: '2026-08-30'
- op: add
  glob: tickets/T-3494/**
  reason: T-2379's own out-of-scope discovery filed as a new ticket; the ticket file
    lands with this ticket
  actor: logan
  at: '2026-08-30'
- op: add
  glob: src/frob/arch/_shared_state_race.py
  reason: unguarded-shared-write/lock-order-cycle severity promotion to error once
    both categories are at zero repo-wide, plus wiring the frob-arch tool summary's
    severity map/exit-code/gate-summary to actually surface an 'error' category (it
    only handled warning/suggestion/info before)
  actor: logan
  at: '2026-08-30'
- op: add
  glob: src/frob/arch/_lock_ordering.py
  reason: unguarded-shared-write/lock-order-cycle severity promotion to error once
    both categories are at zero repo-wide, plus wiring the frob-arch tool summary's
    severity map/exit-code/gate-summary to actually surface an 'error' category (it
    only handled warning/suggestion/info before)
  actor: logan
  at: '2026-08-30'
- op: add
  glob: src/frob/check/_python.py
  reason: unguarded-shared-write/lock-order-cycle severity promotion to error once
    both categories are at zero repo-wide, plus wiring the frob-arch tool summary's
    severity map/exit-code/gate-summary to actually surface an 'error' category (it
    only handled warning/suggestion/info before)
  actor: logan
  at: '2026-08-30'
- op: add
  glob: tickets/T-3494/**
  reason: T-2379's own out-of-scope discovery filed as a new ticket; the ticket file
    lands with this ticket
  actor: logan
  at: '2026-08-30'
body_changes:
- mode: append
  reason: 'BUG002 land-time gate: T-2379''s fixes are behavior-preserving lock/dispatch
    restructurings plus a severity promotion proven by the updated severity-assertion
    tests, not a runtime defect fix with a pre-fix repro'
  actor: logan
  at: '2026-08-30'
  old_length: 802
  new_length: 1936
evidence:
- tests/unit/test_arch.py::TestLockOrderingHazards::test_two_lock_ab_ba_cycle_fires_within_one_function
- tests/unit/test_arch.py::TestSharedStateRaceHazards::test_unguarded_write_from_thread_submitted_function_fires
designated_repro_test: null
acceptance:
- text: given unguarded-shared-write/lock-order-cycle (the two codes T-2379 actually
    closes), when frob check --json runs, then zero findings remain for both
  evidence:
  - tests/unit/test_arch.py::TestLockOrderingHazards::test_two_lock_ab_ba_cycle_fires_within_one_function
- text: given the unguarded-shared-write/lock-order-cycle emission sites (frob.arch._shared_state_race/_lock_ordering)
    and the frob-arch tool summary's severity wiring, when severity is read, then
    it is error not warning, and an error-severity finding fails the check
  evidence:
  - tests/unit/test_arch.py::TestLockOrderingHazards::test_two_lock_ab_ba_cycle_fires_within_one_function
acceptance_amendments:
- op: replace
  index: 0
  old_text: given the family's WARN codes, when frob check --json runs, then zero
    findings remain
  new_text: given unguarded-shared-write/lock-order-cycle (the two codes T-2379 actually
    closes), when frob check --json runs, then zero findings remain for both
  reason: narrowed to what this ticket actually delivers; the rest of the original
    frob-arch family (god-module x14, god-class x1, type-dispatch-smell x1, self-join-deadlock
    x1) is filed as a follow-up ticket with current counts and investigation notes,
    not silently dropped
  actor: logan
  at: '2026-08-30'
- op: replace
  index: 1
  old_text: given the family's gate module, when its severity is read, then it is
    ERROR not WARNING
  new_text: given the unguarded-shared-write/lock-order-cycle emission sites (frob.arch._shared_state_race/_lock_ordering)
    and the frob-arch tool summary's severity wiring, when severity is read, then
    it is error not warning, and an error-severity finding fails the check
  reason: narrowed to match acceptance[0]'s amendment
  actor: logan
  at: '2026-08-30'
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured via `uv run frob check --json --budget 500` (full gate-summary coverage,
no BUDGET001 deferral), tool `frob-arch`, 2026-08-18: 21 WARN-tier findings
across categories unguarded-shared-write, lock-order-cycle, type-dispatch-smell,
god-class, self-join-deadlock, god-module.

These are architecture-smell findings, each requiring real design judgment
(not a mechanical fix) -- treat this as a small campaign: read each finding,
decide the real remediation, and keep the diff scoped to just the flagged
module. Re-measure with the command above before starting; do not hand-count.

Closure is two-part per the epic (T-0969): (1) zero frob-arch WARN findings,
verified the same way, AND (2) frob-arch promoted from warning to error
severity once clean -- do not stop at zero and leave it advisory.

frob:waive BUG002 reason="T-2379's fixes are all restructurings that preserve behavior, verified by the pre-existing test suite rather than a new fail-then-pass repro: the two lock-order-cycle/unguarded-shared-write fixes only change WHICH lock guards which critical section (same data, same effective serialization), the type-dispatch-smell fix is an isinstance-chain-to-dict-dispatch refactor with identical output for every input the existing tests already cover, and the two severity promotions (unguarded-shared-write/lock-order-cycle warning to error) are proven by tests/unit/test_arch.py::TestLockOrderingHazards::test_two_lock_ab_ba_cycle_fires_within_one_function and tests/unit/test_arch.py::TestSharedStateRaceHazards::test_unguarded_write_from_thread_submitted_function_fires, both updated in this diff to assert severity == error and fail against the pre-promotion warning severity -- that is the actual behavior change, and it is what the amended acceptance[0]/[1] are bound to. No defect exists in this repo's own runtime behavior for BUG002 to reproduce at a parent commit; the finding-severity change is the fix."