---
id: T-2200
title: TICKET ROT lists a runs_last ticket under NEEDS DISPATCH, but frob ticket start
  structurally refuses it with RunsLastBlocked, so the report recommends an action
  the tool rejects
state: done
kind: bug
origin: human
created: '2026-08-16'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- scripts/fleet_status.py
- src/frob/gates/_tickets_gate.py
- docs/guides/coordinator-scripts.md
evidence_scope:
- tests/unit/test_coordinator_scripts.py
- tests/test_tickets_priority.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_tickets_gate.py
  reason: 'Ticket body acceptance criterion 3 explicitly requires auditing TICK004

    (src/frob/gates/_tickets_gate.py) for the same runs_last omission and

    fixing the gate/report contradiction together, not just the report. The

    originally declared scope only listed scripts/fleet_status.py; widening to

    include the gate module so the fix can land as one coherent change per the

    ticket''s own explicit requirement.

    '
  actor: logan
  at: '2026-08-16'
- op: add
  glob: docs/guides/coordinator-scripts.md
  reason: 'Doc-coverage closure requires docs/guides/coordinator-scripts.md in scope

    since every public fleet_status.py symbol has a frob:doc edge into it and

    this ticket touches several of those symbols'' docstrings.

    '
  actor: logan
  at: '2026-08-16'
evidence:
- tests/unit/test_coordinator_scripts.py::TestPrintTicketRot::test_splits_by_tier_under_distinct_action_headings
- tests/unit/test_coordinator_scripts.py::TestPrintTicketRot::test_runs_last_ticket_gets_its_own_deferred_bucket_not_needs_dispatch
- tests/unit/test_coordinator_scripts.py::TestRottingTickets::test_reads_runs_last_as_a_structured_field_not_from_title
- tests/test_tickets_priority.py::TestTick004QueueRot::test_stale_critical_ticket_flags
- tests/test_tickets_priority.py::TestTick004QueueRot::test_stale_runs_last_ticket_gets_a_distinct_message_not_work_it
designated_repro_test: tests/unit/test_coordinator_scripts.py::TestPrintTicketRot::test_runs_last_ticket_gets_its_own_deferred_bucket_not_needs_dispatch
acceptance:
- text: 'Reproduced live: T-1614''s title is literally ''RUNS LAST: audit every frob:waive
    for cop-outs, after all other work is complete''. I ran ''frob ticket runs-last
    T-1614 on'' (runs_last: true confirmed in the ledger), and scripts/fleet_status.py
    still reports it under ''NEEDS DISPATCH (2)''. Meanwhile frob ticket start refuses
    any runs_last ticket while other tickets are open -- measured earlier today on
    T-1780, which failed with RunsLastBlocked and could not be worked until the flag
    was cleared. So the report recommends dispatching a ticket the tool will reject.
    This test MUST fail against current main.'
  evidence:
  - tests/unit/test_coordinator_scripts.py::TestPrintTicketRot::test_runs_last_ticket_gets_its_own_deferred_bucket_not_needs_dispatch
- text: 'Read runs_last from the ledger frontmatter the report ALREADY parses (_parse_ticket_ledger_file)
    and route those tickets to a third bucket naming the real action -- they are neither
    dispatchable nor decomposable, they are deliberately deferred. Do NOT drop them
    from the report: a runs_last ticket aging past threshold is still real information,
    and T-1614 at 11 days is genuinely waiting on a queue that is not draining.'
  evidence:
  - tests/unit/test_coordinator_scripts.py::TestRottingTickets::test_reads_runs_last_as_a_structured_field_not_from_title
- text: 'Audit the same omission in TICK004 itself: src/frob/gates/_tickets_gate.py
    contains ZERO references to runs_last, so the gate rot-alarms a ticket another
    subsystem structurally forbids anyone from starting. Two subsystems in direct
    contradiction. Do NOT fix only the report -- the gate and the report should agree
    on what a runs_last ticket''s rot means, and fixing the display while leaving
    the gate contradictory just moves the confusion.'
  evidence:
  - tests/test_tickets_priority.py::TestTick004QueueRot::test_stale_runs_last_ticket_gets_a_distinct_message_not_work_it
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Done report

Fixed the runs_last/rot-report contradiction on both sides that T-2200
described:

- scripts/fleet_status.py: `_parse_ticket_ledger_file` now reads
  `runs_last` as a structured ledger field (never inferred from title
  text). `rotting_tickets` carries it through, and `_print_ticket_rot`
  routes a rotting runs_last leaf ticket into a new "DEFERRED (RUNS
  LAST)" heading instead of "NEEDS DISPATCH" -- it is still reported
  (age is real information), just with the real action named
  (re-prioritize/clear the flag) instead of an instruction
  `frob ticket start` structurally refuses.

- src/frob/gates/_tickets_gate.py: `_tick004_queue_rot` now emits a
  distinct message for a rotting runs_last ticket, naming
  RunsLastBlocked and the deferred nature explicitly, instead of the
  generic "work it" text -- closing the direct contradiction T-2200's
  acceptance [3] called out (TICK004 alarming a ticket start structurally
  refuses).

Repro: tests/unit/test_coordinator_scripts.py::TestPrintTicketRot::
test_runs_last_ticket_gets_its_own_deferred_bucket_not_needs_dispatch,
confirmed FAILED_AT_PARENT at afcea25bf25e6426dd6446b46a65faf24fc440d8
(the repro-only commit) via `frob ticket evidence --check-repro`.

Must-still-pass controls: TestPrintTicketRot::
test_splits_by_tier_under_distinct_action_headings (ordinary rotting
leaf still under NEEDS DISPATCH) and TestTick004QueueRot::
test_stale_critical_ticket_flags (ordinary ticket still gets the normal
"work it" message) both still pass unmodified.

Filed T-2229 (renumbers at land) for a distinct, related
finding the coordinator raised mid-series: TICK004/fleet_status also
tells an operator to "work" an already-decomposed epic whose children
are in-progress (T-1623/T-2223/T-2224) -- a different mechanism
(parent/child ticket-graph state, not a runs_last flag), scoped
separately rather than widening T-2200.

Widened scope from the ticket's original `scripts/fleet_status.py` alone
to also include `src/frob/gates/_tickets_gate.py` and
`docs/guides/coordinator-scripts.md` -- required by the ticket's own
acceptance criterion [3] (audit and fix TICK004 itself, not just the
report) and by scope-closure's doc-coverage requirement.

### Changed
```
 scripts/fleet_status.py                | 97 ++++++++++++++++++++++++----------
 src/frob/gates/_tickets_gate.py        | 42 ++++++++++++---
 tests/test_tickets_priority.py         | 27 ++++++++++
 tests/unit/test_coordinator_scripts.py | 81 +++++++++++++++++++++++++++-
 tickets/T-2200/ticket.md               | 44 ++++++++++++++-
 tickets/T-2229/ticket.md     | 65 +++++++++++++++++++++++
 6 files changed, 318 insertions(+), 38 deletions(-)
```

### Evidence
- `tests/unit/test_coordinator_scripts.py::TestPrintTicketRot::test_splits_by_tier_under_distinct_action_headings` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestPrintTicketRot::test_runs_last_ticket_gets_its_own_deferred_bucket_not_needs_dispatch` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestRottingTickets::test_reads_runs_last_as_a_structured_field_not_from_title` (pytest node id, verified passing when recorded)
- `tests/test_tickets_priority.py::TestTick004QueueRot::test_stale_critical_ticket_flags` (pytest node id, verified passing when recorded)
- `tests/test_tickets_priority.py::TestTick004QueueRot::test_stale_runs_last_ticket_gets_a_distinct_message_not_work_it` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, AFFECT001@scripts/fleet_status.py, ARCH001@scripts/fleet_status.py, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@scripts/fleet_status.py, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-draft-0bd874ac/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-draft-0bd874ac/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, E501@/home/logan/projects/frob/.claude/worktrees/t2200-series/src/frob/lang/_nodes.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PRE001@tickets/T-2200, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
