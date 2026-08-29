---
id: T-2639
title: Wire WAIVE009 into frob check + document in gates.md
state: done
kind: bug
origin: human
created: '2026-08-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/__init__.py
- src/frob/gates/_waive.py
- docs/modules/gates.md
- tests/test_waive_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: docs/modules/gates.md
  reason: docs/modules/gates.md is under T-2613's live lease; narrow to code-only,
    will re-add once free
  actor: logan
  at: '2026-08-19'
- op: add
  glob: src/frob/gates/_waive.py
  reason: must remove the T-2639-premised COV001 waiver on waive009_violations once
    wiring+docs land
  actor: logan
  at: '2026-08-19'
- op: add
  glob: docs/modules/gates.md
  reason: T-2613 released the lease; adding the doc half of the plan
  actor: logan
  at: '2026-08-19'
- op: add
  glob: docs/modules/gates.md
  reason: T-2613 released the lease; adding the doc half of the plan
  actor: logan
  at: '2026-08-19'
- op: add
  glob: tests/test_waive_gate.py
  reason: add end-to-end wiring repro test proving WAIVE009 fires through run_gates,
    not just the direct unit-level call
  actor: logan
  at: '2026-08-19'
- op: add
  glob: tests/test_waive_gate.py
  reason: add end-to-end wiring repro test proving WAIVE009 fires through run_gates,
    not just the direct unit-level call
  actor: logan
  at: '2026-08-19'
evidence:
- tests/test_waive_gate.py::TestWaive009Wiring::test_unresolvable_promise_fires_through_run_gates
- tests/test_waive_gate.py::TestWaive009Wiring::test_resolvable_promise_also_fires_through_run_gates
designated_repro_test: tests/test_waive_gate.py::TestWaive009Wiring::test_unresolvable_promise_fires_through_run_gates
evidence_changes:
- old_node: tests/test_waive_gate.py::TestWaive009Wiring::test_resolvable_promise_does_not_fire_through_run_gates
  new_node: tests/test_waive_gate.py::TestWaive009Wiring::test_resolvable_promise_also_fires_through_run_gates
  reason: T-3295 renamed this test (WAIVE009 now fires even when the cited ticket
    resolves)
  actor: logan
  at: '2026-08-29'
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 6c794282205b949f04dcef3c77a290f945d1d0ae
---
## Description

T-2606 implements WAIVE009 (`src/frob/gates/_waive.py::waive009_violations`,
`_reason_promises_followup`, `_reason_ticket_ids`) -- a `frob:waive` reason
that promises deferred/future work (a follow-up ticket, "once X clears",
"will file", ...) but names no ticket id that resolves in the queue.
Fully implemented and unit-tested directly against `frob.gates._waive`
(14 passing tests, `tests/test_waive_gate.py::TestWaive009*`), and
`WAIVE009` is registered in `_KNOWN_GATE_RULES`.

It is NOT yet wired into `frob check`: `_assemble_gate_report` in
`src/frob/gates/__init__.py` is where every other WAIVE00* self-check
(WAIVE001/002/005/008, waive006_gate, waive007_gate) is called into the
up-front violations list, and that file was under a LIVE in-progress
lease (T-2580, scope `src/frob/gates/_milestone.py` +
`src/frob/gates/__init__.py`) for T-2606's entire working window, so
`frob ticket scope T-2606 --add src/frob/gates/__init__.py` refused with
`ScopeLeaseConflict`. `docs/modules/gates.md`'s gate catalog (where every
other WAIVE00* rule has its own subsection) was ALSO under a live lease
at the same time (T-2377). Forcing either add would have collided with
two different sibling agents' active work -- not done.

## Plan

1. Once T-2580 (and, separately, T-2377 for the doc half) closes/narrows
   its lease off these two files: add one line to `_assemble_gate_report`
   calling `*waive009_violations(st.snapshot, st.queue)` alongside the
   other WAIVE00* self-checks (same dependency shape as waive006_gate/
   waive007_gate -- needs only the snapshot's waive edges + merged ticket
   queue, no assembled violation set), and re-export `waive009_violations`
   from the `frob.gates._waive` import block near the other WAIVE00*
   imports.
2. Add a WAIVE009 subsection to `docs/modules/gates.md`'s gate catalog,
   matching the WAIVE006/007/008 subsections' shape.
3. Re-run `tests/test_waive_gate.py` plus a real `frob check --only
   gates-fast` (or whichever stage group carries the WAIVE00* self-checks)
   to confirm the newly-wired rule actually fires end-to-end, not just at
   the unit level.

## Acceptance

- [0] given a `frob:waive` reason promising follow-up work with no
      resolvable ticket id, when `frob check` runs (no `--only`
      restriction excluding the WAIVE family), then a WAIVE009 ERROR is
      reported -- not just importable/callable from `frob.gates._waive`
      directly.
- [1] `docs/modules/gates.md` documents WAIVE009 alongside WAIVE006/007/008.