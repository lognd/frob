---
id: T-2602
title: 'test_doable_sprint_filter has been red on main since T-1995: the duplicate-title
  guard fires on its own fixture'
state: done
kind: bug
origin: human
created: '2026-08-19'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/test_app_runners_t0715_sprint_tier.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/test_app_runners_t0715_sprint_tier.py::TestTicketDoableSprintByParent::test_doable_sprint_filter
designated_repro_test: tests/unit/test_app_runners_t0715_sprint_tier.py::TestTicketDoableSprintByParent::test_doable_sprint_filter
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 9a5a8defe8e2e827b2f28a7ce51a3c0daed94635
---
## Measured on unmodified main

    uv run pytest tests/unit/test_app_runners_t0715_sprint_tier.py::\
      TestTicketDoableSprintByParent::test_doable_sprint_filter
    -> FAILED (SystemExit: 1)

Cause is visible in the captured log. The fixture files two tickets whose
titles are similar ("in sprint"), and T-1995's duplicate-title guard
refuses the second:

    WARNING ticket new: 1 existing ticket(s) closely match this title --
            review before filing a duplicate:
    WARNING   T-0001 [queued] (82% match): in sprint
    ERROR   ticket new: refusing -- pass --ack-related once you have
            confirmed this is not a duplicate of the ticket(s) above

So a guard is firing on its own test suite's fixture. The guard is
CORRECT; the fixture predates it and was never updated when T-1995 landed.

## Why this matters more than one red test

This test has been failing since T-1995 landed, on unmodified main, with
nothing surfacing it. Every agent that runs a touched-set or scoped test
selection sees green because this file is not in their touched set, and
anyone who does hit it reasonably concludes they broke it. It was found
today only because an agent working an unrelated ticket happened to run it
and mentioned it in prose -- it was filed nowhere.

A permanently-red test is strictly worse than a deleted one: it consumes
the signal that a red test is supposed to carry.

## Fix

Pass `--ack-related` in the fixture (the guard's own intended escape
hatch), or give the two fixture tickets titles that are not near-duplicates.
Prefer whichever keeps the test's ACTUAL subject -- doable/sprint filtering
by parent -- unchanged; the near-duplicate titles look incidental to what
this test is asserting, not load-bearing.

Do NOT weaken, skip, or xfail the T-1995 guard to make this pass. The guard
caught a real duplicate-shaped filing, which is exactly its job.

## Also worth determining, and filing separately if true

Whether OTHER tests broke the same way when T-1995 landed. A guard added
without sweeping the existing fixtures usually breaks more than one. Run the
full `tests/unit/` selection and report how many are red on unmodified main
before fixing, so the denominator is known -- if there are others, they are
the same class and this ticket should say so rather than silently fixing
only the one that happened to be noticed.

## Positive controls, both directions

- the fixed test PASSES on unmodified main
- the T-1995 duplicate-title guard STILL refuses a genuine near-duplicate
  filing that does not pass `--ack-related` -- without this case the fix is
  indistinguishable from disabling the guard
- the test still asserts what it was written to assert (sprint filtering by
  parent), verified by checking it fails if that behavior is broken