---
id: T-0925
title: 'docs: add lock-ordering hazards section to docs/modules/arch.md'
state: done
kind: docs
origin: human
created: '2026-07-26'
priority: medium
parent: T-0694
tier: ticket
sprint: null
scope:
- docs/modules/arch.md
- src/frob/arch/_lock_ordering.py
- tests/unit/test_arch.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_arch.py
  reason: docs-only ticket still needs evidence test file scope-add per playbook section
    4
  actor: logan
  at: '2026-07-27'
evidence:
- tests/unit/test_arch.py::TestLockOrderingHazards::test_two_lock_ab_ba_cycle_fires_within_one_function
designated_repro_test: null
threat: null
component: null
---
docs/modules/arch.md needs a "Lock-ordering hazards" section documenting
`lock-order-cycle`/`lock-identity-unresolved` (frob.arch._lock_ordering,
T-0694, child 2 of the T-0693 concurrency-hazard umbrella), matching the
existing "Fork/pool hazards" (T-0695) and "Async event-loop hazards"
(T-0696) sections' structure/detail level. T-0694's own scope
(src/frob/arch/**, tests/unit/test_arch.py) does not include docs/, so no
frob:doc anchor was added on the check function in that ticket -- add the
section and the frob:doc directive together here.