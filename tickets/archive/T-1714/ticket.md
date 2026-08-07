---
id: T-1714
title: '4 regressions on main from the T-1679 series: T-1637''s evidence broken by
  a rename, plus 2 ty parameter-default errors'
state: done
kind: bug
origin: agent
created: '2026-08-06'
priority: critical
parent: null
tier: ticket
sprint: null
scope:
- tests/unit/test_ticket_runner_gate_findings.py
- tests/unit/test_ticket_store.py
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_ticket_store.py::TestWriteTicket::test_non_strict_opt_out_warns_loudly_instead_of_refusing
- tests/unit/test_ticket_store.py::TestWriteTicket::test_content_loss_refuses_by_default
designated_repro_test: null
threat: null
component: null
---
Main went from 3 errors to 7 across the T-1673/T-1630/T-1675/T-1670/
T-1679 land series. All four new errors are attributable to that series
and none of them was caught, because the post-land sweep that exists to
catch exactly this is currently blind (T-1703).

1. TWO COV003 -- T-1679 BROKE A CLOSED TICKET'S EVIDENCE.

       T-1637 evidence 'tests/unit/test_ticket_store.py::TestWriteTicket::
       test_content_loss_warns_loudly_by_default' does not resolve
       ... ::TestWriteTicket::test_strict_no_content_loss_refuses -- same

   T-1679 inverted the content-loss guard default and renamed/reshaped
   those tests. T-1637 is DONE and bound its evidence to them, so its
   evidence no longer resolves. This is the known "a refactor invalidates
   doc/test/waiver edges OUTSIDE the refactoring ticket's own scope"
   class: `--ticket`-scoped verification structurally cannot see it,
   because the broken edge belongs to a different ticket.

   Fix by re-binding T-1637's evidence to the tests as they now exist
   (`frob ticket evidence T-1637 --replace ...`), NOT by restoring the old
   test names -- T-1679's rename was the intended change. Confirm the
   re-bound ids genuinely exercise the same behaviour T-1637 claimed;
   a binding that resolves but tests something else is worse than a
   broken one.

2. TWO ty invalid-parameter-default in
   tests/unit/test_ticket_runner_gate_findings.py:41-42

       Default value of type `tuple[()]` is not assignable to annotated
       parameter type `list[tuple[str, str, str]]`

   A `()` default on a `list`-annotated parameter. Fix the annotation or
   the default so they agree; do not suppress it.

WHY THIS TICKET EXISTS AS A TICKET. Each land in that series reported
green under `--ticket` scoping and each post-land sweep reported CLEAN.
Both were true statements about a narrower question than "is main
healthy". The scoped check cannot see cross-ticket edges by design, and
the unscoped sweep that exists to cover that gap is the one T-1703 shows
can read zero on a dirty tree. Two safety nets with a shared blind spot
is one safety net.

So: after fixing the four errors, run an UNSCOPED `frob check` on main
and confirm the count returns to the 3 known pre-existing errors (the
`ty` unresolved-attribute in test_ticket_work_and_land_finish.py, ARCH001
in _evidence.py, DOC009 on the 2026-08-06 audit file -- all tracked by
T-1685). A `--ticket`-scoped zero does not close this ticket.