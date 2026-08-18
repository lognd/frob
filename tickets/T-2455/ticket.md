---
id: T-2455
title: related-title duplicate detector false-positives on holder/collider, breaking
  a pre-existing start test
state: queued
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_new.py
- tests/unit/test_app_runners_batch7.py
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
Found while working T-2394: `tests/unit/test_app_runners_batch7.py::
TestTicketStart::test_start_refuses_scope_colliding_with_other_in_progress_
lease` fails on current main (confirmed byte-identical file content
against main, unrelated to T-2394's own changes) --
`frob.app.ticket_runner._new`'s related-title duplicate detector
(`related_tickets`/`_ack_related`) reports a 71% match between "holder"
and "collider" and refuses the second `frob ticket new` call the test
relies on, before the test ever reaches the scope-collision assertion it
is meant to check.

REPRODUCED:
  $ pytest tests/unit/test_app_runners_batch7.py::TestTicketStart::test_start_refuses_scope_colliding_with_other_in_progress_lease
  ... refusing -- pass --ack-related once you have confirmed this is not a duplicate ...

FIX: either raise the fuzzy-match threshold so "holder"/"collider" no
longer trips it, or have the test pass `ticket_ack_related=True` on its
second `frob ticket new` call (the same escape hatch a real caller would
use). Whichever direction, add a regression test locking in the chosen
threshold/behavior.
