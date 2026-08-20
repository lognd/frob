---
id: T-2726
title: disclosure_shaped_language signal 1 (phrase match) scans the whole ticket body,
  not just the Done report
state: queued
kind: bug
origin: human
created: '2026-08-20'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_reporting.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
`frob.tickets._reporting.disclosure_shaped_language`'s signal 1 (the
`_DISCLOSURE_PHRASES` match) is called by
`_undisclosed_remainder_reason` against the ticket's FULL `body` --
description and Plan sections included, not scoped to the `## Done
report` section the way signal 2 (`_done_report_section`) already is.

Measured directly while validating T-2718's own fix: T-2718's own
ticket DESCRIPTION quotes the exact phrase "named no follow-up" (as
its own subject matter, describing the bug), which trips signal 1
against the ticket's OWN close -- independent of anything in its Done
report, and independent of T-2718's own fix (which only scoped
signal 2). A ticket whose bug report or plan happens to discuss
disclosure/follow-up language as its SUBJECT -- exactly what a
ticket ABOUT this guard is likely to do -- can never close cleanly
even with a perfectly clean Done report.

Fix: scope signal 1's scan to `_done_report_section(text)` the same
way signal 2 already is, instead of the full `text`/`ticket.body`.
Positive control both directions: a Description that discusses
"not attempted" etc. as its own subject must not block close; a
genuine phrase disclosure INSIDE the Done report itself must still
fire exactly as today.

Found while working T-2718.
