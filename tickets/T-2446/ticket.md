---
id: T-2446
title: 55 open tickets hold glob-shaped scopes and 20 lease the whole test suite,
  capping fleet parallelism
state: done
kind: bug
origin: human
created: '2026-08-18'
priority: high
parent: null
tier: epic
sprint: null
runs_last: false
scope:
- src/frob/_cli_parsers/_ticket/_progress.py
- src/frob/app/ticket_runner/_lifecycle.py
- tests/unit/test_app_runners_batch7.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/_cli_parsers/_ticket/_progress.py
  reason: 'part a: wire --scope-breadth-ack/--scope-breadth-ack-reason onto start,
    mandatory when the T-1866 guard would otherwise refuse; part b done via direct
    ticket-CLI scope edits on the 55 flagged tickets, no source scope needed for those'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/ticket_runner/_lifecycle.py
  reason: 'part a: wire --scope-breadth-ack/--scope-breadth-ack-reason onto start,
    mandatory when the T-1866 guard would otherwise refuse; part b done via direct
    ticket-CLI scope edits on the 55 flagged tickets, no source scope needed for those'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/unit/test_app_runners_batch7.py
  reason: existing TestTicketStart suite for the T-1866 refuse-over-broad guard this
    ticket extends with inline ack flags
  actor: logan
  at: '2026-08-18'
evidence:
- tests/unit/test_app_runners_batch7.py::TestTicketStart::test_start_scope_breadth_ack_flag_sets_field_before_refusal
- tests/unit/test_app_runners_batch7.py::TestTicketStart::test_start_scope_breadth_ack_without_reason_refuses
- tests/unit/test_app_runners_batch7.py::TestScopeBreadthNarrowingT2446::test_conftest_contention_materially_reduced
- tests/unit/test_app_runners_batch7.py::TestScopeBreadthNarrowingT2446::test_narrowed_disjoint_tickets_have_no_scope_overlap
- tests/unit/test_app_runners_batch7.py::TestScopeBreadthNarrowingT2446::test_narrowed_sibling_tickets_still_conflict
designated_repro_test: null
acceptance:
- text: Given a ticket whose declared scope contains an over-broad glob, when frob
    ticket start runs without an explicit breadth acknowledgement and reason, then
    it is refused rather than merely warned.
  evidence:
  - tests/unit/test_app_runners_batch7.py::TestTicketStart::test_start_scope_breadth_ack_flag_sets_field_before_refusal
  - tests/unit/test_app_runners_batch7.py::TestTicketStart::test_start_scope_breadth_ack_without_reason_refuses
- text: Given the 20 tickets currently appearing on every contended test file, when
    their scopes have been narrowed, then frob ticket contention reports a materially
    lower ticket count on tests/conftest.py, with the before and after numbers recorded.
  evidence:
  - tests/unit/test_app_runners_batch7.py::TestScopeBreadthNarrowingT2446::test_conftest_contention_materially_reduced
  - tests/unit/test_app_runners_batch7.py::TestScopeBreadthNarrowingT2446::test_narrowed_disjoint_tickets_have_no_scope_overlap
  - tests/unit/test_app_runners_batch7.py::TestScopeBreadthNarrowingT2446::test_narrowed_sibling_tickets_still_conflict
- text: Given two tickets declaring different individual test files, when both are
    started, then both succeed concurrently, which is impossible today.
  evidence:
  - tests/unit/test_app_runners_batch7.py::TestScopeBreadthNarrowingT2446::test_conftest_contention_materially_reduced
  - tests/unit/test_app_runners_batch7.py::TestScopeBreadthNarrowingT2446::test_narrowed_disjoint_tickets_have_no_scope_overlap
  - tests/unit/test_app_runners_batch7.py::TestScopeBreadthNarrowingT2446::test_narrowed_sibling_tickets_still_conflict
- text: Given a ticket with a genuinely conflicting narrow scope, when it is started,
    then it is still refused, proving breadth was not fixed by weakening lease detection.
  evidence:
  - tests/unit/test_app_runners_batch7.py::TestScopeBreadthNarrowingT2446::test_conftest_contention_materially_reduced
  - tests/unit/test_app_runners_batch7.py::TestScopeBreadthNarrowingT2446::test_narrowed_disjoint_tickets_have_no_scope_overlap
  - tests/unit/test_app_runners_batch7.py::TestScopeBreadthNarrowingT2446::test_narrowed_sibling_tickets_still_conflict
threat: null
component: tickets
anchor: false
anchor_reason: null
land_commit: 62feac2eef699074f27cb9a0c41b5bb8ab6ca222
---
Scope is simultaneously the evidence-coverage declaration AND the write
lease, so an over-broad scope on an idle ticket silently caps how many
agents can work at once. Measured today with the newly-landed
`frob ticket contention` (T-2395):

    open tickets:                                403
    with >=1 glob-shaped scope entry:             55  (13.6%)
    appearing on EVERY contended test file:       20

That second number is the damaging one. `frob ticket contention` ranks
`tests/test_arch_gate.py`, `tests/test_release.py`,
`tests/test_ticket_land.py`, `tests/conftest.py` and every other test
file at "21 tickets" -- and it is the SAME 20 ids on every row
(T-1135, T-1137, T-1597, T-1599..T-1666, T-1945), plus whichever single
ticket is really working that file. They are not contending over shared
code; they each declare `tests/**` or similar and are therefore leasing
the entire test suite.

Spot-checked five: T-1135 (3 of 3 scope entries glob-shaped), T-1137
(4 of 4), T-1599 (3 of 5), T-1656 (2 of 4), T-1945 (2 of 2). ALL FIVE
ARE `queued` -- none has started. So twenty tickets doing no work are
blocking every ticket that touches any test file, which is nearly all
of them.

THE GUARD ALREADY EXISTS AND IS ROUTINELY IGNORED. `OVER_BROAD_LITERAL_
GLOBS` (`src/frob/tickets/_models.py`) explicitly lists `tests/**`,
`tests/`, `docs/`, `docs/**`, `src/frob/**`, `src/frob/`, and its own
comment says these are "the specific globs that have actually caused
over-hiding in this repo's history ... flagged unconditionally by
`large_glob_warnings`, before the file-count threshold is even
consulted". It is a WARNING at `ticket new` time. It has now been
ignored 55 times.

This is structurally the same defect T-2394 just fixed for EMPTY scope:
the condition was detected at filing time as advice, and only bit much
later at a point where it was expensive. T-2394's answer was to refuse
at `frob ticket start`, because start is where the lease is actually
taken. Apply the same reasoning here -- a warning nobody must act on is
not a control.

TWO HALVES, and the ticket is not done without both:

**(a) Stop the bleeding.** Make an over-broad scope a REFUSAL at
`frob ticket start`, not merely a warning at `ticket new`. As with
T-2394, a ticket that legitimately needs a broad scope must be able to
DECLARE that explicitly (with a reason), so declared-broad and
carelessly-broad are distinguishable. There is precedent in the CLI
already: `--scope-breadth-ack`/`--scope-breadth-ack-reason` exist on
`ticket new`. Wire the same acknowledgement to `start` and make it
mandatory rather than optional.

**(b) Narrow the existing 55.** Per-ticket judgement, not a bulk
rewrite. For each: if it is an epic that should be decomposed
(T-1135, T-1137, T-1219 and T-1599 are ALREADY flagged as
NEEDS DECOMPOSITION by `fleet_status.py`, aged 20-21 days), narrowing
the parent's scope to its own ledger files is usually right, since the
children carry the real file scopes. If it is a genuine leaf with a
broad scope, narrow it to the files it will actually touch. Do NOT
narrow by guessing -- read what each ticket is for. Prioritise the 20
that appear on every test row; they are the entire parallelism cap.

VERIFICATION:
  - Re-run `frob ticket contention` before and after and report the
    delta in the top row's ticket count. Going from "21 tickets" to a
    small number on `tests/conftest.py` is the measurable outcome.
  - must-still-refuse: a ticket with a genuinely conflicting narrow
    scope must still be refused at start. Do not solve breadth by
    weakening lease detection.
  - must-now-start: two tickets touching DIFFERENT test files must both
    be startable concurrently, which is impossible today.