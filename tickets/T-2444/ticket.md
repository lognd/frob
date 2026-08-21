---
id: T-2444
title: Fix pre-existing duplicate-title SystemExit failures in test_app_runners_t1738_wave.py
state: done
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/test_app_runners_t1738_wave.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/test_app_runners_t1738_wave.py::TestWaveCommand::test_json_render_shape
- tests/unit/test_app_runners_t1738_wave.py::TestWaveCommand::test_plain_render_lists_groups_and_remainder
designated_repro_test: tests/unit/test_app_runners_t1738_wave.py::TestWaveCommand::test_json_render_shape
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 1b23dcb9557789cc778768d16fc9cd91f12a775a
---
tests/unit/test_app_runners_t1738_wave.py::TestWaveCommand::test_json_render_shape
and ::test_plain_render_lists_groups_and_remainder both fail with
SystemExit: 1 on current main, unrelated to any in-flight change:

ticket new: 1 existing ticket(s) closely match this title -- review
before filing a duplicate: T-0001 [queued] (100% match): a ticket

Both tests' shared `_new(tmp_path, ...)` helper files two tickets with
the identical literal title "a ticket" in the same tmp_path -- the
`related_tickets`/duplicate-title refusal (ticket new: refusing --
pass --ack-related ...) now fires on the second call, which used to be
allowed. Reproduced by running the file in isolation against a clean
worktree with no other changes present.

Fix: either pass `ticket_ack_related=True` in the shared `_new` helper
(matching the workaround used in
tests/unit/test_app_runners_t2395_contention.py's own `_new`), or give
each call a distinct title. Whichever lands, confirm both wave tests
pass again.