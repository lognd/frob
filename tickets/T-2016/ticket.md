---
id: T-2016
title: design a growth-rate grammar for frob sys capacity --at DATE
state: in-progress
kind: feature
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/strata/kernel.md
- docs/strata/reliability.md
- src/frob/strata/_capacity.py
evidence_scope:
- tests/unit/strata/test_capacity_projection.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/strata/kernel.md
  reason: design deliverable is documentation, not code -- add the two docs the grammar
    design and its capacity-evaluator cross-reference live in
  actor: logan
  at: '2026-08-10'
- op: add
  glob: docs/strata/reliability.md
  reason: design deliverable is documentation, not code -- add the two docs the grammar
    design and its capacity-evaluator cross-reference live in
  actor: logan
  at: '2026-08-10'
- op: remove
  glob: src/frob/strata/**
  reason: design-only ticket produced a docs deliverable plus a docstring cross-reference;
    narrow off the epic-wide glob to just the files actually touched
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/strata/_capacity.py
  reason: design-only ticket produced a docs deliverable plus a docstring cross-reference;
    narrow off the epic-wide glob to just the files actually touched
  actor: logan
  at: '2026-08-10'
evidence:
- tests/unit/strata/test_capacity_projection.py::TestProjectCapacityUnscaled::test_over_capacity_current_demand_fires
- tests/unit/strata/test_capacity_projection.py::TestProjectCapacityScaled::test_population_scales_demand_linearly
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
docs/strata/roadmap.md's "CLI surface (target)" names `frob sys capacity
[--population N | --at DATE]` as a phase-5 verb. T-1927 implemented the
`--population N` half (`frob.strata._capacity::project_capacity`,
docs/strata/reliability.md#population-projected-capacity-t-1927) but
deliberately cut `--at DATE`: projecting to a calendar date needs a
growth-rate declaration on `Node.users`/`rate` that the T-0702 demand-
propagation grammar (docs/strata/kernel.md#demand-declarations-t-0702)
does not have today -- inventing one is a surface-language change, out
of T-1927's "an evaluator over the model as it exists" scope.

Needed before `--at DATE` is meaningful: a growth-rate declaration
grammar (e.g. `users N growth RATE per PERIOD`) plus the date-projection
arithmetic in `project_capacity` (or a sibling entrypoint) that resolves
a target `--at` date against that rate to a population, then reuses the
same `--population`-style scaling this ticket already built. Filed as a
residue of T-1927 rather than folded into it, per that ticket's own
scope note on why `--at DATE` was cut.