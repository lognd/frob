---
id: T-2455
title: related-title duplicate detector false-positives on holder/collider, breaking
  a pre-existing start test
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
- src/frob/app/ticket_runner/_new.py
- tests/unit/test_app_runners_batch7.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/test_app_runners_batch7.py::TestTicketStart::test_short_dissimilar_titles_are_not_flagged_as_related
- tests/unit/test_app_runners_batch7.py::TestTicketStart::test_start_refuses_scope_colliding_with_other_in_progress_lease
designated_repro_test: tests/unit/test_app_runners_batch7.py::TestTicketStart::test_short_dissimilar_titles_are_not_flagged_as_related
designated_repro_changes:
- old_value: tests/unit/test_app_runners_batch7.py::TestTicketStart::test_start_refuses_scope_collision_between_short_dissimilar_titles
  new_value: tests/unit/test_app_runners_batch7.py::TestTicketStart::test_short_dissimilar_titles_are_not_flagged_as_related
  reason: "Manually verified genuine pre-fix failure by editing _RELATED_TICKET_SIMILARITY_THRESHOLD\
    \ back to 0.6 in the worktree (no commit boundary available for --check-repro's\
    \ ancestor-based merge-base resolution, since the new dedupe-replacement test\
    \ was authored AFTER the fix commit and no pre-fix ancestor commit contains it)\
    \ and running:\n  pytest tests/unit/test_app_runners_batch7.py::TestTicketStart::test_short_dissimilar_titles_are_not_flagged_as_related\n\
    Result: AssertionError -- assert (('T-0001', 'holder', 'queued', 0.7142857142857143),)\
    \ == () -- the exact false-positive match this ticket fixes. Reverted the threshold\
    \ back to 0.8 immediately after and reconfirmed the suite green."
  actor: logan
  at: '2026-08-18'
evidence_changes:
- old_node: tests/unit/test_app_runners_batch7.py::TestTicketStart::test_start_refuses_scope_collision_between_short_dissimilar_titles
  new_node: tests/unit/test_app_runners_batch7.py::TestTicketStart::test_short_dissimilar_titles_are_not_flagged_as_related
  reason: stale evidence id -- test was renamed/replaced in this ticket's own dedupe
    fix (DUP002); the surviving test is already recorded separately
  actor: logan
  at: '2026-08-18'
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