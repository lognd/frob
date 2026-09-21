---
id: T-3614
title: add --wait mode to ticket write verbs
state: done
kind: ux
origin: human
created: '2026-08-31'
priority: medium
blocked_by:
- T-4548
- T-4550
parent: T-3611
tier: ticket
sprint: v0.533.0
runs_last: false
milestone: 0.532.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/_cli_parsers/_ticket
- src/frob/app/ticket_runner/_lifecycle.py
- tests/unit/test_ticket_verbs_wait.py
- src/frob/_cli_parsers/_ticket/_new.py
- src/frob/_cli_parsers/_ticket/_metadata.py
- src/frob/app/ticket_runner/__init__.py
- src/frob/app/config.py
- src/frob/_cli_parsers/_ticket/_closeout_evidence.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/_cli_parsers/_ticket
  reason: --wait flag on the ticket write verbs and their runner
  actor: logan
  at: '2026-09-15'
- op: add
  glob: src/frob/app/ticket_runner/_lifecycle.py
  reason: --wait flag on the ticket write verbs and their runner
  actor: logan
  at: '2026-09-15'
- op: add
  glob: tests/unit/test_ticket_verbs_wait.py
  reason: --wait flag on the ticket write verbs and their runner
  actor: logan
  at: '2026-09-15'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_new.py
  reason: new verb --wait flag
  actor: logan
  at: '2026-09-16'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_metadata.py
  reason: body/scope/accept/scope-ack --wait flag
  actor: logan
  at: '2026-09-16'
- op: add
  glob: src/frob/app/ticket_runner/__init__.py
  reason: shared pre-dispatch LandInProgress choke point every write verb passes through
  actor: logan
  at: '2026-09-16'
- op: add
  glob: src/frob/app/config.py
  reason: add the ticket_wait_s AppConfig field the shared LandInProgress dispatch
    check reads; documented as blocked on this exact edit in the tickets own failure
    log
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_closeout_evidence.py
  reason: drop and fail verbs are parsed here; this tickets own plan names them among
    the six --wait verbs, and T-4550 (the prior lease holder) is now done
  actor: logan
  at: '2026-09-20'
triage_changes:
- field: priority
  old_value: high
  new_value: medium
  reason: 'T-4483 follow-up: TICK004 escalated to error on 2026-09-15 (15d queued
    > 2x the 7d high threshold) and reds every CI leg; these are T-3611 latency-epic
    children, sprint v0.532.0 work behind the v0.531.0 alpha cut, not alpha-path work,
    so medium is the honest priority'
  actor: logan
  at: '2026-09-14'
- field: sprint
  old_value: null
  new_value: v0.532.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-15'
- field: milestone
  old_value: null
  new_value: 0.532.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-15'
- field: sprint
  old_value: v0.532.0
  new_value: v0.535.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
- field: sprint
  old_value: v0.535.0
  new_value: v0.533.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
body_changes:
- mode: append
  reason: record blocking lease conflicts found while scoping T-3614
  actor: logan
  at: '2026-09-16'
  old_length: 674
  new_length: 3132
evidence:
- tests/unit/test_ticket_verbs_wait.py::TestDispatchWait::test_window_opens_mid_wait_then_succeeds
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Write verbs that hit LandInProgress or a held lock fail instantly
(0.6s), forcing every caller (agents, coordinator, humans) to hand-roll
sleep loops that miss brief open windows. Add `--wait [SECONDS]`
(default off; sensible default budget when given bare) to
new/drop/body/scope/fail/reconcile: block on the contended lock with
backoff + jitter, succeed the moment the window opens, fail loudly with
the holder's identity (pid + ticket) at budget exhaustion. The holder
identity is already computed for the refusal message -- reuse it.
Tests: window opens mid-wait -> success; budget exhausted -> named
holder in the error. Doc: agent briefs stop prescribing sleep loops.


Blocked (2026-09-16, implementer session):

--wait needs a new AppConfig field (e.g. ticket_wait_s) that every write
verb's parser sets and that the shared pre-dispatch LandInProgress check
(_refuse_if_land_in_progress_for_dispatch in
src/frob/app/ticket_runner/__init__.py:547, called from run() at line
876) reads and threads into refuse_if_land_in_progress's existing
wait_timeout_s parameter (src/frob/tickets/_leases.py already supports
this: the T-1961/T-2023 poll-with-backoff loop in
refuse_if_land_in_progress is fully built, it just is never called with
a caller-supplied wait_timeout_s from the CLI today).

Adding that field requires editing src/frob/app/config.py. Confirmed
empirically that pydantic AppConfig has no extra='allow' escape hatch:
c.ticket_wait_s = 5.0 raises ValueError("AppConfig object has no field
ticket_wait_s") -- there is no way to carry the flag's value from argparse
to the dispatch check without a declared field on that model.

config.py is currently leased by in-progress T-4548 (see
tickets/T-4548: "config.py residue left by T-4535", itself
deferred behind T-3613's lease per the root tickets.md commit log). A
`frob ticket scope T-3614 --add src/frob/app/config.py` attempt was
refused: "ERROR: tickets: T-3614 cannot lease an add glob: held by
in-progress T-4548 (scope 'src/frob/app/config.py')".

Independently, four of the nine target verbs (fail, evidence, drop,
done-report) have their argparsers in
src/frob/_cli_parsers/_ticket/_closeout_evidence.py, which is leased by
a second in-progress ticket, T-4550 ("frob ticket done-report
spawns a full unscoped frob check per call..."). That ticket's own scope
list names that exact file. Even if config.py freed up, those four verbs
would still be blocked by this second collision.

Per the brief's hard rule ("a lease refusal naming another ticket means
stop and report, never --steal"), this ticket cannot proceed until
T-4548 releases config.py, and (for fail/evidence/drop/
done-report specifically) until T-4550 releases
_closeout_evidence.py.

No code was changed. No files outside the worktree were touched.
Suggested next step for the coordinator: land or requeue
T-4548 and T-4550 first, then re-open T-3614 with
its scope re-narrowed to the freed files, or split T-3614 into two
children (metadata-verb --wait vs closeout-verb --wait) gated on each
lease individually.