---
id: T-0879
title: Wire derived_state_lock's EXCLUSIVE side into .frob writers (mutate/doctor/dup/graph)
state: done
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/mutate/**
- src/frob/doctor.py
- src/frob/dup/**
- src/frob/graph/**
- tests/test_mutate.py
- tests/test_doctor.py
- docs/guides/install.md
- docs/modules/mutate.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_mutate.py
  reason: unit tests proving the exclusive-lock wiring live alongside the writers
    they cover
  actor: logan
  at: '2026-07-26'
- op: add
  glob: tests/test_doctor.py
  reason: unit tests proving the exclusive-lock wiring live alongside the writers
    they cover
  actor: logan
  at: '2026-07-26'
- op: add
  glob: docs/guides/install.md
  reason: doc updates for the T-0879 exclusive-lock wiring (AFFECT001 closure docs)
  actor: logan
  at: '2026-07-26'
- op: add
  glob: docs/modules/mutate.md
  reason: doc updates for the T-0879 exclusive-lock wiring (AFFECT001 closure docs)
  actor: logan
  at: '2026-07-26'
evidence:
- tests/test_mutate.py::test_run_mutations_holds_exclusive_lock_blocking_a_shared_reader
- tests/test_doctor.py::test_run_diagnosis_holds_exclusive_lock_blocking_a_shared_reader
designated_repro_test: null
threat: null
component: null
---
T-0859 shipped `frob.process._lock.derived_state_lock`, a cross-process
shared/exclusive flock over `.frob/derived.lock`, and wired the SHARED
(reader) side into every `frob.check` entry point (`run_check`,
`run_check_cpp`, `run_check_rust`, `run_check_ts`) so a check run holds
it for its entire duration -- precheck through the last stage's read.

That closes the cross-process TOCTOU window between two frob CHECK
processes, but the EXCLUSIVE (writer) side of the contract is not yet
held by any current writer of `.frob`'s derived artifacts: `frob mutate`,
`frob doctor`'s rebuild path, and `frob.dup`/`frob.graph`'s cache
rebuilders can still rewrite `.frob/cache.db`/`dup.db`/`baseline` etc.
while a `frob check` reader holds the shared lock, or while another
writer is also mid-rebuild, with no serialization at all today.

Wire `derived_state_lock(root, exclusive=True)` into each of those
writer call sites (out of T-0859's `src/frob/check/**` +
`src/frob/process/**` scope -- this ticket covers `src/frob/mutate/**`,
`src/frob/doctor.py`, `src/frob/dup/**`, `src/frob/graph/**` as needed)
so the reader/writer contract `derived_state_lock`'s docstring already
describes is actually enforced end to end, not just documented as an
aspiration on the reader side.

See docs/modules/process.md's "Derived-state lock (T-0859)" section and
src/frob/process/_lock.py's module docstring for the primitive and its
contract.