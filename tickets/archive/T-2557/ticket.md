---
id: T-2557
title: 'no gate catches an in-progress ticket with an EMPTY scope: SCOPE001 is diff-driven,
  TICK009 only checks breadth'
state: done
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_tickets_gate.py
- src/frob/gates/_waive.py
- docs/modules/gates.md
- tests/test_tick013_gate.py
- design/frob.strata
- docs/modules/tickets-lifecycle.md
- docs/design/registry/capability-via-ratchet.lock.json
- docs/design/registry/check-coverage.yaml
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_tickets_gate.py
  reason: declare real scope for TICK013 empty-scope gate implementation
  actor: logan
  at: '2026-08-21'
- op: add
  glob: src/frob/gates/_waive.py
  reason: declare real scope for TICK013 empty-scope gate implementation
  actor: logan
  at: '2026-08-21'
- op: add
  glob: docs/modules/gates.md
  reason: declare real scope for TICK013 empty-scope gate implementation
  actor: logan
  at: '2026-08-21'
- op: add
  glob: tests/test_tick013_gate.py
  reason: declare real scope for TICK013 empty-scope gate implementation
  actor: logan
  at: '2026-08-21'
- op: add
  glob: design/frob.strata
  reason: SELFAUDIT001 exec-capability declaration for new test file, AFFECT001 doc-closure
    for tickets_gate change
  actor: logan
  at: '2026-08-21'
- op: add
  glob: docs/modules/tickets-lifecycle.md
  reason: SELFAUDIT001 exec-capability declaration for new test file, AFFECT001 doc-closure
    for tickets_gate change
  actor: logan
  at: '2026-08-21'
- op: add
  glob: docs/design/registry/capability-via-ratchet.lock.json
  reason: SYS111 exec-capability ratchet bump for the new test file's subprocess use
  actor: logan
  at: '2026-08-21'
- op: add
  glob: docs/design/registry/check-coverage.yaml
  reason: 'REG009/REG010: register CHK-GATE-TICK013 entry'
  actor: logan
  at: '2026-08-21'
evidence:
- tests/test_tick013_gate.py::TestTick013EmptyScope::test_in_progress_empty_scope_fires
- tests/test_tick013_gate.py::TestTick013EmptyScope::test_planned_empty_scope_fires
- tests/test_tick013_gate.py::TestTick013EmptyScope::test_queued_empty_scope_is_silent
- tests/test_tick013_gate.py::TestTick013EmptyScope::test_nonempty_scope_is_silent
- tests/test_tick013_gate.py::TestTick013EmptyScope::test_declared_no_scope_is_silent
- tests/test_tick013_gate.py::TestTick013EmptyScope::test_terminal_state_empty_scope_is_silent
designated_repro_test: tests/test_tick013_gate.py::TestTick013EmptyScope::test_in_progress_empty_scope_fires
acceptance:
- text: given a ticket in state in-progress or planned whose scope is empty and which
    has not declared --declare-no-scope, when the tickets gate runs, then a finding
    names that ticket id
  evidence:
  - tests/test_tick013_gate.py::TestTick013EmptyScope::test_in_progress_empty_scope_fires
  - tests/test_tick013_gate.py::TestTick013EmptyScope::test_planned_empty_scope_fires
  - tests/test_tick013_gate.py::TestTick013EmptyScope::test_nonempty_scope_is_silent
  - tests/test_tick013_gate.py::TestTick013EmptyScope::test_queued_empty_scope_is_silent
- text: given a ticket that has declared --declare-no-scope, when the tickets gate
    runs, then no such finding is produced for it
  evidence:
  - tests/test_tick013_gate.py::TestTick013EmptyScope::test_in_progress_empty_scope_fires
  - tests/test_tick013_gate.py::TestTick013EmptyScope::test_planned_empty_scope_fires
  - tests/test_tick013_gate.py::TestTick013EmptyScope::test_queued_empty_scope_is_silent
  - tests/test_tick013_gate.py::TestTick013EmptyScope::test_nonempty_scope_is_silent
  - tests/test_tick013_gate.py::TestTick013EmptyScope::test_declared_no_scope_is_silent
- text: given a ticket in a terminal state (done, dropped, failed) with an empty scope,
    when the tickets gate runs, then no such finding is produced for it
  evidence:
  - tests/test_tick013_gate.py::TestTick013EmptyScope::test_declared_no_scope_is_silent
  - tests/test_tick013_gate.py::TestTick013EmptyScope::test_terminal_state_empty_scope_is_silent
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 9b6c83d0a74cf3e638b6cf71dfe9e700960c12ce
---
Found by walking into the state, not by reading code: T-2377 sat
`state: in-progress` with `scope: []` for roughly an hour, holding a
worktree lease, and not one gate fired on it.

WHY NOTHING CATCHES IT. There are two candidate detectors and each one
misses for a different structural reason:

- SCOPE001 (`frob.gates.scope_gate`) is DIFF-driven. Its docstring is
  explicit that an empty scope is deliberately not a free pass -- and
  that is true, per touched FILE. But the finding is produced by
  iterating the diff's touched files, so a ticket whose worktree is
  clean (everything already landed, or work not started) touches
  nothing, the loop body never runs, and the riskiest ticket state in
  the ledger reads as clean. The guard is correct about the file it
  sees and blind to the state itself.
- TICK009 (`frob.gates._tickets_gate`) IS the ledger-scan detector for
  this exact state -- it already iterates every `IN_PROGRESS`/`PLANNED`
  ticket, which is the loop this needs -- but it only ever asks whether
  a scope is too BROAD (`large_glob_warnings`). The symmetric and
  strictly more dangerous case, a scope that is EMPTY, is not asked
  about at all.

WHY IT MATTERS MORE THAN THE BROAD CASE TICK009 ALREADY WARNS ON. A
broad scope over-locks files and slows the fleet down loudly. An empty
scope holds a real worktree lease while declaring NO stated intent, so
nothing can be checked against it: SCOPE001 has no globs to enforce,
`frob ticket land` has no scope to test cross-ticket leakage against,
and a reader of `frob ticket doable` sees an in-progress ticket that
looks live. `frob ticket start` already refuses an empty scope at write
time (T-2394), which is exactly why this state looks impossible and is
not monitored -- but `frob ticket scope --remove` can empty it AFTER
the start, and that is how it was reached here.

PROPOSED FIX (cheap -- the loop already exists): a new TICK rule in the
same `IN_PROGRESS`/`PLANNED` scan TICK009 uses, firing when a non-
terminal ticket's `scope` is empty AND it has not declared
`--declare-no-scope`. That declaration is the existing, first-class
opt-out for a legitimately scope-free ticket (a tier=epic rollup, a
pure decision record), so the rule has a correct exemption from day
one and does not need a new waiver channel.

Severity: ERROR is defensible given T-2394 already refuses the state at
`start`, but WARN-first matches this repo's own promotion convention
(T-0688/T-0728) -- decide when implementing, and count the ledger first.