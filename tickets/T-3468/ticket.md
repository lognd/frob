---
id: T-3468
title: done-report does not mirror to primary checkout; body-append/Done-report heading
  collision unresolved
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
- src/frob/app/ticket_runner/**
- src/frob/tickets/_reporting.py
- tests/test_tickets_body.py
- tests/unit/test_ticket_runner_ledger_mirror.py
- docs/modules/tickets-data-storage.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_tickets_body.py
  reason: add coverage for defect 2 (done-report visibility warning) and defect 3
    (body --append ambiguous Done-report-heading message) fixes
  actor: logan
  at: '2026-08-30'
- op: add
  glob: tests/unit/test_ticket_runner_ledger_mirror.py
  reason: add coverage for defect 2 (done-report visibility warning) and defect 3
    (body --append ambiguous Done-report-heading message) fixes
  actor: logan
  at: '2026-08-30'
- op: add
  glob: docs/modules/tickets-data-storage.md
  reason: 'AFFECT001: documenting T-3468''s BodyTextAmbiguousSection error-message
    pointer to done-report'
  actor: logan
  at: '2026-08-30'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while working T-3336.

T-3336 fixed defect 1 (close's rapid-profile bypass covering the
missing-evidence/Done-report check that land's own NotCloseable gate
never relaxes -- src/frob/tickets/_evidence.py::_done_transition_
structural_guard). Two more defects from the same filing remain
unaddressed because their code lives well outside that narrow fix:

DEFECT 2: `frob ticket done-report` does not mirror a worktree write
back to the primary checkout, unlike `body`/`evidence`/`new`. An agent
has to run it twice (once in the worktree so land sees it, once
directly against root so main has it), and the two independently-
generated copies can produce an add/add merge conflict on
tickets/<id>/done-report.md.

Candidate fix: wire `done-report`'s CLI dispatch the same way
`body`/`evidence`/`new` already mirror onto the primary checkout, or
document at the point of use (--help text, docstring) that it does not
and name what to run instead.

DEFECT 3 (heading collision): `frob ticket body --append` refuses text
containing the literal `## Done report` heading as an ambiguous edit
target (BodyTextAmbiguousSection), while land's NotCloseable gate
requires exactly that heading to be present. An agent working around
the append refusal by avoiding the heading text produces a Done report
land's own gate cannot see.

Candidate fix: make the two rules aware of each other -- e.g. `body
--append` could special-case a `## Done report` append as "use `frob
ticket done-report` instead" rather than a generic ambiguous-section
refusal, since that verb exists specifically to write this heading
correctly.

THIRD FIXTURE from the original ticket body ("done-report written in a
worktree is visible in the primary checkout without a second manual
invocation, and produces no add/add conflict") is NOT covered by
T-3336's landed fix -- it needs defect 2's mirroring fix.
