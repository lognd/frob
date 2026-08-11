---
id: T-2093
title: refuse_if_land_in_progress poll loop never observes its exit condition; three
  tests hang and it runs on the live dispatch path
state: done
kind: bug
origin: agent
created: '2026-08-10'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_leases.py
- tests/test_ticket_leases.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_ticket_leases.py
  reason: 'Root cause is a test-authoring gap, not a src defect: the three hanging

    tests never override refuse_if_land_in_progress''s 330s production default

    wait budget (frob.toml [tickets] land_wait_timeout_s), and each holds

    land.lock IN-PROCESS for the whole assertion, so the deadline is

    structurally unreachable before the full budget elapses. The fix and its

    bounded repro both live in the test file alongside the existing sibling

    test (test_refuses_while_land_lock_held) that already uses this exact

    override pattern.

    '
  actor: logan
  at: '2026-08-10'
evidence:
- tests/test_ticket_leases.py::TestRefuseIfLandInProgress::test_concurrent_land_and_ticket_new_cannot_corrupt_the_ledger
- tests/test_ticket_leases.py::TestDispatchLandGuard::test_refuses_mutating_verb_while_land_in_progress
- tests/test_ticket_leases.py::TestDispatchLandGuard::test_refused_verb_never_writes_the_ticket_file_at_all
- tests/test_ticket_leases.py::TestRefuseIfLandInProgress::test_refuses_while_land_lock_held
- tests/test_ticket_leases.py::TestDispatchLandGuard::test_land_verb_itself_is_exempt
- tests/test_ticket_leases.py::TestDispatchLandGuard::test_read_only_verb_runs_while_land_in_progress
designated_repro_test: tests/test_ticket_leases.py::TestRefuseIfLandInProgress::test_concurrent_land_and_ticket_new_cannot_corrupt_the_ledger
acceptance:
- text: given no land is actually in progress, when refuse_if_land_in_progress is
    called on the dispatch path, then it returns within an asserted upper bound rather
    than polling indefinitely -- this test MUST fail (hang) against current main
  evidence:
  - tests/test_ticket_leases.py::TestRefuseIfLandInProgress::test_concurrent_land_and_ticket_new_cannot_corrupt_the_ledger
- text: given the three named tests in tests/test_ticket_leases.py, when the suite
    runs, then all three complete rather than hanging
  evidence:
  - tests/test_ticket_leases.py::TestDispatchLandGuard::test_refuses_mutating_verb_while_land_in_progress
  - tests/test_ticket_leases.py::TestDispatchLandGuard::test_refused_verb_never_writes_the_ticket_file_at_all
- text: given a land genuinely IS in flight, when a mutating ticket verb is dispatched,
    then it still refuses or waits as before -- the guard is not weakened
  evidence:
  - tests/test_ticket_leases.py::TestRefuseIfLandInProgress::test_refuses_while_land_lock_held
  - tests/test_ticket_leases.py::TestDispatchLandGuard::test_land_verb_itself_is_exempt
  - tests/test_ticket_leases.py::TestDispatchLandGuard::test_read_only_verb_runs_while_land_in_progress
threat: null
component: tickets
labels:
- hang
- fleet-blocking
anchor: false
anchor_reason: null
---
## Measured evidence

Three tests HANG indefinitely rather than fail. Each was re-run in isolation
with `-n0` and each stalls inside the SAME code path --
`refuse_if_land_in_progress`, `src/frob/tickets/_leases.py:1742`, blocked in
its poll `sleep()`:

  tests/test_ticket_leases.py::TestRefuseIfLandInProgress::test_concurrent_land_and_ticket_new_cannot_corrupt_the_ledger
  tests/test_ticket_leases.py::TestDispatchLandGuard::test_refuses_mutating_verb_while_land_in_progress
  tests/test_ticket_leases.py::TestDispatchLandGuard::test_refused_verb_never_writes_the_ticket_file_at_all

Three independent call sites, one line. That is a poll loop that does not
observe its exit condition, not three unrelated flaky tests.

## Why this is critical rather than a test-only defect

`refuse_if_land_in_progress` is NOT test-only. It runs on the DISPATCH path:

  src/frob/app/ticket_runner/__init__.py:653
    _refuse_if_land_in_progress_for_dispatch(root, cfg.ticket_command)
  src/frob/app/ticket_runner/__init__.py:494
    refused = refuse_if_land_in_progress(root)

i.e. on `frob ticket <verb>` invocations generally (T-1619 originally ran it
only inside a narrower path; it was widened). A wait loop that can fail to
observe its exit condition on the dispatch path can hang ANY ticket command,
for any operator or agent, until an external timeout kills it.

## A hypothesis to test, NOT a claim

A `frob ticket doable` run of mine exceeded a 500s timeout and was killed. I
attributed that to the measured 207.5s sweep revalidation (T-2089). 207.5s
does not obviously add up to >500s. This hang is a candidate second
contributor. Do NOT assume it -- instrument and find out. If it is
unrelated, say so; T-2089 remains the known-real cost either way.

## What to establish

The loop's structure is a deadline poll: it warns "waiting for in-flight
land to finish (up to %.0fs more)" and then
`sleep(min(poll_interval_s, deadline - now))`. Determine why the exit
condition is never observed in these three tests. Candidates worth checking
explicitly rather than guessing:
 - `_land_flock_probe` / `_scan_for_live_land_process` reporting a live land
   that has actually exited (a stale lock file, or a pid that is reused or
   belongs to the test's own process tree)
 - a deadline that is never reached because `deadline - now` cannot go
   non-positive (clock source, or a deadline recomputed each iteration)
 - the probe detecting the TEST's own process as the landing process

## DO NOT FIX IT THIS WAY

- **Do not fix it by shortening the timeout or the poll interval.** That
  converts an indefinite hang into a shorter hang; the loop still never
  observes its exit condition. Find why the condition is not observed.
- **Do not fix it by making the tests skip, xfail, or use a shorter deadline
  fixture.** These three tests are the only current evidence of a defect on
  a live dispatch path. Silencing them removes the signal, not the bug.
- **Do not weaken the guard into a non-blocking check.** Refusing or waiting
  while a land is in flight is deliberate and protects the ledger; a guard
  that stops waiting would reintroduce the corruption T-1619 exists to
  prevent.
- **Do not treat a hang as a flake.** It reproduced deterministically, in
  isolation, three times, on the same line.

## Acceptance direction

The first test must fail (hang) against current main and pass after: the
three named tests complete, and a dispatch-path invocation cannot block
indefinitely when no land is actually running. Include an upper bound that
is ASSERTED, not assumed -- a test that would hang forever on regression is
itself a hazard, so bound it.