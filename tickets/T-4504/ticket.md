---
id: T-4504
title: 'Scope check/_python.py: thread file-set into ruff/ty/gate spawns for scoped
  land checks'
state: queued
kind: feature
origin: human
created: '2026-09-15'
priority: medium
parent: null
tier: ticket
sprint: v0.540.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/check/_python.py
- src/frob/check/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.540.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while working T-4413 (blocked/failed as scoped).

T-4413 asked for the rapid land's synchronous pre-land check to become
compute-scoped (diff-touched files + direct dependents) so a one-file
land's check completes under 3 minutes. T-4413's declared scope was
_land_cmd.py, src/frob/verify, _verify.py, check_runner.py,
gates/__init__.py -- none of which contain the actual compute floor.

Measured/documented facts (from _verify.py's own
_shared_check_spawn_fn docstring, corroborating T-4413's attempt-1
measurement of 465s warm for a 1-file ticket):

- ruff/ty/frob-arch/frob-cycle/frob-dup/frob-exports (check/_python.py)
  run unconditionally over the WHOLE root on every invocation
  (_run_ruff calls ruff check with str(root) and no path narrowing) --
  this is the ~150s floor even with the T-1346 gate cache fully warm,
  and it is untouched by --only/--delta (both filter REPORTED findings
  only, never computation -- see _shared_check_spawn_fn's docstring).
- gates/__init__.py's run_gates/_run_gates_bounded (in T-4413's scope)
  dispatches ~90 gates over a snapshot built by build_graph, which
  itself parses every file in the tree; scoping the individual gate
  functions in gates/__init__.py cannot reduce this floor without also
  scoping check/_python.py's tool invocations, since those dominate
  wall-clock per the docstring's own measurement breakdown.

To make a genuinely scoped land check possible, run_check/_python_tasks
(check/__init__.py) and _run_ruff/_run_ty/etc (check/_python.py) need an
explicit file-set parameter that narrows the ruff/ty/native-tool argv
to the diff-touched-files-plus-dependents set _land_cmd.py already
computes (or can compute via frob.affects), falling back to the
current whole-root behavior when no file set is given so every
existing caller (CI, plain frob check) is unaffected. T-4413 (or a
successor ticket, once this lands) then wires that parameter through
_shared_check_spawn_fn/_land_core_invoke under the rapid profile.

Also needed: a per-gate classification (already-repo-wide gates such
as ledger/milestone/release/tickets/cross_ticket_leakage must keep
running unscoped, with a one-line reason each) once gates/__init__.py's
run_gates can accept a file set.