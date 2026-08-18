---
id: T-2498
title: frob ticket body --append silently misroutes into done-report.md when one exists
state: done
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_setters.py
- src/frob/tickets/__init__.py
evidence_scope:
- tests/test_tickets_body.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/test_tickets_body.py::TestBodyAmend::test_append_after_done_report_targets_raw_body_not_report_file
- tests/test_tickets_body.py::TestBodyAmend::test_append_of_structural_heading_text_refused
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 5cbb6f1eb4f177b587f55785136bdcc578602e13
---
Found while working T-2452: `frob ticket body <id> --append TEXT --reason
TEXT` silently misdirects its write when the target ticket already has a
done-report.md.

Reproduction: ran `frob ticket body T-2452 --append 'frob:no-behavior-change
reason="..."' --reason '...'` on a ticket that already had a Done report
recorded (tickets/T-2452/done-report.md existed). The command reported
success ("T-2452: body append (now 5681 chars)") and recorded a
body_changes ledger entry (old_length: 5117, new_length: 5681) in
tickets/T-2452/ticket.md's front matter. But the ACTUAL free-text body
written under ticket.md's second `---` delimiter was left completely
unchanged (633 chars, the original plan text) -- the appended text
instead landed at the end of tickets/T-2452/done-report.md.

Root cause hypothesis (not confirmed via source read, just behavioral):
`_load_ticket_and_queue`'s loader appears to compute an in-memory
`ticket.body` that concatenates the raw ticket.md body with
done-report.md's rendered content when a done report exists (confirmed
via direct `uv run python3 -c "from frob.tickets import
_load_ticket_and_queue; ..."` -- the loaded `Ticket.body` was 5117/5682
chars, matching plan-text + done-report content, not the 633-char raw
file). `set_body`'s append operates on this composite `old_body`, and
`write_ticket` (or an intermediate split step) appears to route the
appended tail back into done-report.md instead of the true ticket.md
body field it was asked to modify.

Impact: any caller relying on `frob ticket body --append` to add a
`frob:no-behavior-change reason="..."` (or ANY) directive to a ticket
that already has a done-report.md gets a false-success report and a
directive that lands in the wrong file. In this instance the directive
happened to still be visible to BUG002 (which apparently reads the same
composite-body view at gate time), so the workaround succeeded, but this
is fragile and surprising -- any consumer that reads raw
`tickets/T-####/ticket.md` body text directly (not through this same
loader) would never see the appended content.

Suggest: either (1) `set_body`/`_load_ticket_and_queue` should compute
`ticket.body` as ONLY the raw ticket.md body (never silently
concatenating done-report.md content into it), with done-report display
handled separately at render time, or (2) if the composite view is
intentional for display, `set_body`'s write path must correctly persist
an append back into the TRUE ticket.md body field regardless of whether
a done-report exists, not partition it into done-report.md.