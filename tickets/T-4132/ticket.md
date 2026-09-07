---
id: T-4132
title: py.typed is declared in package-data but does not exist and is absent from
  the built wheel, so frob ships untyped and every scaffolded project inherits the
  same false claim
state: in-progress
kind: bug
origin: agent
created: '2026-09-06'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- pyproject.toml
- src/frob/scaffold/data/shared/python/pyproject.toml.j2
- src/frob/py.typed
- src/frob/scaffold/project.py
- src/frob/scaffold/data/shared/python/py.typed.j2
- tests/system/test_packaging_py_typed.py
- tickets/T-4133/ticket.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/py.typed
  reason: T-4132 requires creating the actual py.typed marker file, wiring it into
    the scaffold manifest so generated projects get the file (not just the declaration),
    and a wheel-inspection fixture -- these are the concrete deliverables the ticket
    body demands; narrower initial scope only covered the two config declarations
  actor: logan
  at: '2026-09-06'
- op: add
  glob: src/frob/scaffold/project.py
  reason: T-4132 requires creating the actual py.typed marker file, wiring it into
    the scaffold manifest so generated projects get the file (not just the declaration),
    and a wheel-inspection fixture -- these are the concrete deliverables the ticket
    body demands; narrower initial scope only covered the two config declarations
  actor: logan
  at: '2026-09-06'
- op: add
  glob: src/frob/scaffold/data/shared/python/py.typed.j2
  reason: T-4132 requires creating the actual py.typed marker file, wiring it into
    the scaffold manifest so generated projects get the file (not just the declaration),
    and a wheel-inspection fixture -- these are the concrete deliverables the ticket
    body demands; narrower initial scope only covered the two config declarations
  actor: logan
  at: '2026-09-06'
- op: add
  glob: tests/system/test_packaging_py_typed.py
  reason: T-4132 requires creating the actual py.typed marker file, wiring it into
    the scaffold manifest so generated projects get the file (not just the declaration),
    and a wheel-inspection fixture -- these are the concrete deliverables the ticket
    body demands; narrower initial scope only covered the two config declarations
  actor: logan
  at: '2026-09-06'
- op: add
  glob: design/frob.strata
  reason: 'T-4132 closure requirements: the new fixture''s subprocess exec must be
    declared in design/frob.strata''s testsuite node (SELFAUDIT001, same pattern test_artifact_smoke.py
    already uses); widening project.py''s scope pulled in its existing frob:doc/frob:tests
    closure targets (SCOPE002) which are pure declare-only leases, no edits made to
    them; and the mirrored follow-up ticket T-4133''s own ticket.md needs to be in
    scope since filing it from this worktree wrote that file (SCOPE001).'
  actor: logan
  at: '2026-09-07'
- op: add
  glob: docs/commands/scaffold.md
  reason: 'T-4132 closure requirements: the new fixture''s subprocess exec must be
    declared in design/frob.strata''s testsuite node (SELFAUDIT001, same pattern test_artifact_smoke.py
    already uses); widening project.py''s scope pulled in its existing frob:doc/frob:tests
    closure targets (SCOPE002) which are pure declare-only leases, no edits made to
    them; and the mirrored follow-up ticket T-4133''s own ticket.md needs to be in
    scope since filing it from this worktree wrote that file (SCOPE001).'
  actor: logan
  at: '2026-09-07'
- op: add
  glob: tests/system/test_scaffold_dx.py
  reason: 'T-4132 closure requirements: the new fixture''s subprocess exec must be
    declared in design/frob.strata''s testsuite node (SELFAUDIT001, same pattern test_artifact_smoke.py
    already uses); widening project.py''s scope pulled in its existing frob:doc/frob:tests
    closure targets (SCOPE002) which are pure declare-only leases, no edits made to
    them; and the mirrored follow-up ticket T-4133''s own ticket.md needs to be in
    scope since filing it from this worktree wrote that file (SCOPE001).'
  actor: logan
  at: '2026-09-07'
- op: add
  glob: tests/test_scaffold_worktree_lease_hook.py
  reason: 'T-4132 closure requirements: the new fixture''s subprocess exec must be
    declared in design/frob.strata''s testsuite node (SELFAUDIT001, same pattern test_artifact_smoke.py
    already uses); widening project.py''s scope pulled in its existing frob:doc/frob:tests
    closure targets (SCOPE002) which are pure declare-only leases, no edits made to
    them; and the mirrored follow-up ticket T-4133''s own ticket.md needs to be in
    scope since filing it from this worktree wrote that file (SCOPE001).'
  actor: logan
  at: '2026-09-07'
- op: add
  glob: tickets/T-4133/ticket.md
  reason: 'T-4132 closure requirements: the new fixture''s subprocess exec must be
    declared in design/frob.strata''s testsuite node (SELFAUDIT001, same pattern test_artifact_smoke.py
    already uses); widening project.py''s scope pulled in its existing frob:doc/frob:tests
    closure targets (SCOPE002) which are pure declare-only leases, no edits made to
    them; and the mirrored follow-up ticket T-4133''s own ticket.md needs to be in
    scope since filing it from this worktree wrote that file (SCOPE001).'
  actor: logan
  at: '2026-09-07'
- op: remove
  glob: design/frob.strata
  reason: revert overbroad widen -- design/frob.strata pulls in 241 unrelated closure
    obligations, need a narrower path for SELFAUDIT001/SCOPE002
  actor: logan
  at: '2026-09-07'
- op: remove
  glob: docs/commands/scaffold.md
  reason: revert overbroad widen -- design/frob.strata pulls in 241 unrelated closure
    obligations, need a narrower path for SELFAUDIT001/SCOPE002
  actor: logan
  at: '2026-09-07'
- op: remove
  glob: tests/system/test_scaffold_dx.py
  reason: revert overbroad widen -- design/frob.strata pulls in 241 unrelated closure
    obligations, need a narrower path for SELFAUDIT001/SCOPE002
  actor: logan
  at: '2026-09-07'
- op: remove
  glob: tests/test_scaffold_worktree_lease_hook.py
  reason: revert overbroad widen -- design/frob.strata pulls in 241 unrelated closure
    obligations, need a narrower path for SELFAUDIT001/SCOPE002
  actor: logan
  at: '2026-09-07'
designated_repro_test: null
acceptance:
- text: given a wheel built from this repository, when its contents are listed, then
    a py.typed marker is present at the package root
  evidence: []
- text: given a freshly scaffolded python project, when a wheel is built from it,
    then that wheel contains its own py.typed marker
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
FROB SHIPS WITHOUT A py.typed MARKER, so every downstream type checker treats it
as UNTYPED and silently ignores the annotations on its entire public API. Found
while verifying badge claims for the release-presentation ticket, before writing
a "typed" badge that would have been false.

MEASURED, three independent checks:

  1. pyproject.toml line 233 declares "py.typed" in the package-data list, so
     the packaging config asserts the marker ships.
  2. `git ls-files | grep py.typed` returns NOTHING. The file does not exist in
     the repository at all.
  3. The most recent built wheel in dist/ contains ZERO entries matching
     py.typed. The claim in (1) is not merely untested, it is false in the
     artifact we would publish.

So the declaration is satisfied by nothing. Setuptools' package-data does not
error on a pattern that matches no file -- it simply includes nothing -- which
is why this has been invisible. That is the silent-zero shape at the packaging
layer, and it is the same class as the zero-match declaration glob just fixed for
strata declarations: a rule matching nothing reads exactly like a rule satisfied.

WHAT IT COSTS CONSUMERS. Per the typing specification, a package without the
marker is not type-checked by its consumers at all -- an importing project's
checker skips frob's annotations entirely and treats every frob symbol as
untyped. Every annotation in this codebase is therefore doing nothing for anyone
downstream. For a tool whose own gates enforce type discipline, shipping
un-introspectable types is a poor advertisement as well as a real loss.

IT PROPAGATES TO EVERY SCAFFOLDED PROJECT. The same declaration is templated
into the shared python scaffold's generated packaging config, which means every
project frob scaffolds inherits the identical claim. If the generated tree does
not also create the marker file, every downstream project has this defect too --
and would have no reason to suspect it. CHECK THE SCAFFOLD OUTPUT DIRECTLY; do
not infer it from the template.

WHAT TO DO
  1. Add the marker file to the package and confirm it lands in a built wheel by
     inspecting the wheel, not by re-reading the config.
  2. Add a fixture that inspects a BUILT ARTIFACT for the marker. A test that
     reads pyproject.toml would have passed throughout this entire period; only
     an artifact-level check catches it. This repo has already learned that
     reading a derived record instead of the artifact produces a wrong answer.
  3. Fix the scaffold so generated projects get the marker file, not just the
     declaration, and verify by scaffolding into a temp directory and building.
  4. Consider whether a gate should fail when a package-data pattern matches no
     file. That is the general form of this bug and would have caught it.

MUST-FIRE FIXTURE:   a built wheel contains the marker at the package root.
MUST-STAY-QUIET:     no other packaged data file is dropped or duplicated by the
                     change.
THIRD FIXTURE:       a freshly scaffolded project builds a wheel that contains
                     its own marker.

ACCEPTANCE
- The marker exists and is verified present in a built wheel by inspecting the
  wheel.
- The scaffold produces it for generated projects, verified by building one.
- A package-data pattern matching zero files is either made a gate failure or
  explicitly ruled out with a reason.
- All three fixtures committed.
