---
id: T-4316
title: Closing T-4298 stranded its own frob:todo directive, failing the gate step
state: done
kind: bug
origin: human
created: '2026-09-08'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_land_format.py
- tickets/T-4323/**
- tests/unit/test_land_format_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tickets/T-4323/**
  reason: filing the auto-apply follow-up ticket this fix rebinds the frob:todo to
  actor: logan
  at: '2026-09-08'
- op: add
  glob: docs/modules/gates.md
  reason: close SCOPE002 doc/test closure surfaced by the frob:todo rebind edit
  actor: logan
  at: '2026-09-08'
- op: add
  glob: tests/unit/test_land_format_gate.py
  reason: close SCOPE002 doc/test closure surfaced by the frob:todo rebind edit
  actor: logan
  at: '2026-09-08'
- op: remove
  glob: docs/modules/gates.md
  reason: gates.md is a monofile hub whose anchors cascade scope closure across the
    repo; reverting, will use --demote-to-evidence-only or a waiver instead for the
    single land_format_gate doc-target requirement
  actor: logan
  at: '2026-09-08'
body_changes:
- mode: append
  reason: 'unblock BUG002 at land time: this bug ticket''s fix is a directive-citation
    rebind, not executable logic a mutation-killing test could target

    '
  actor: logan
  at: '2026-09-08'
  old_length: 2176
  new_length: 2610
evidence:
- tests/test_todo_fmt_gate.py::TestTodo002Edges::test_open_ticket_no_violation
- tests/test_todo_fmt_gate.py::TestTodo002Edges::test_closed_ticket_fires_todo002
- tests/test_todo_fmt_gate.py::TestTodo002Edges::test_missing_ticket_fires_todo002
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
CLOSING A TICKET STRANDED A DEFERRED-WORK DIRECTIVE THAT NAMED IT, FAILING THE
GATE STEP. THIS IS THE SECOND INSTANCE OF THIS EXACT CLASS TODAY.

THE FAILURE. The unscoped gate run reports one TODO002 error: a deferred-work
directive in the land-formatting gate's own module names the ticket that
introduced that module, and that ticket is now closed, so the directive is no
longer bound to an open ticket. Nobody edited the directive or the code around it;
the ticket closing is what broke it.

THE IDENTICAL SHAPE ALREADY HAPPENED HOURS EARLIER with a waiver rather than a
deferred-work marker: a waiver naming a ticket as its follow-up started failing
the moment that ticket closed, and was repaired separately. Two different directive
families, one mechanism -- a comment names a ticket id, the ticket reaches a
terminal state, and a gate that requires the id to be open turns red with no code
change. Expect more of these; several directive families in this codebase can name
a ticket.

DECIDE WHAT THE DIRECTIVE ACTUALLY MEANS BEFORE REBINDING IT. Read what the marked
work is. If the deferred work is genuinely still outstanding, it needs a real open
ticket describing it, and that ticket is the correct binding -- do not point it at
an unrelated open id to clear the error. If the work was in fact completed as part
of the closing ticket and the marker is simply residue, the right fix is deleting
the marker, not rebinding it. Say which you found and why.

THEN ADDRESS THE RECURRENCE, since a second instance in one day of the same
mechanism is the signal. A ticket already exists proposing a warning at close time
for the waiver family; check whether it is filed and whether its framing covers
directive families generally rather than only waivers, and if it does not, say so
in this ticket so the two are not fixed narrowly and separately. Do not build that
check here -- this ticket is the unblock.

VERIFY by running the unscoped gate check and confirming the TODO002 error is gone.
Expect other errors to remain from a separate ticket covering the architecture
gate; those are not yours. Quote the error count you actually see rather than
asserting a clean run.

frob:waive BUG002 reason="comment/directive-rebind-only fix: the diff changes a citation in a code comment (frob:todo T-4298 -> T-4323), not executable logic. tests/test_todo_fmt_gate.py::TestTodo002Edges already exercises the TODO002 open/closed-ticket mechanism this rebind relies on; no mutation of gate logic can distinguish a citation change, so a genuinely-failing-then-passing repro test cannot exist for this defect class."