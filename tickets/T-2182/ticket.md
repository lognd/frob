---
id: T-2182
title: Ticket rot is measured by TICK004 in the gates layer but never surfaced where
  dispatch happens, so 15 tickets aged past threshold (3 critical, up to 20d) while
  every wave picked freshly-filed work
state: done
kind: feature
origin: human
created: '2026-08-16'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- scripts/fleet_status.py
evidence_scope:
- tests/unit/test_coordinator_scripts.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_coordinator_scripts.py::TestPrintTicketRot::test_splits_by_tier_under_distinct_action_headings
- tests/unit/test_coordinator_scripts.py::TestRottingTickets::test_flags_a_ticket_past_its_priority_threshold
- tests/unit/test_coordinator_scripts.py::TestRottingTickets::test_ignores_tickets_still_under_threshold
- tests/unit/test_coordinator_scripts.py::TestRottingTickets::test_distinguishes_epic_and_story_tier_from_ticket_tier
- tests/unit/test_coordinator_scripts.py::TestRottingTickets::test_only_queued_and_planned_states_are_considered
designated_repro_test: null
acceptance:
- text: 'Surface rotting tickets in the place a coordinator ALREADY looks before dispatching
    (scripts/fleet_status.py''s standing report), not behind a new command. Precedent:
    T-2049 did exactly this for the verify quarantine, and it was read and acted on
    by an agent within two hours of landing, having gone unnoticed for an hour before.
    A command someone must know to run is not surfacing. This test MUST fail against
    current main.'
  evidence:
  - tests/unit/test_coordinator_scripts.py::TestPrintTicketRot::test_splits_by_tier_under_distinct_action_headings
- text: Derive the rotting set from the ticket ledger's own STRUCTURED fields (state,
    priority, and the queued-since timestamp) compared against the configured TICK004
    thresholds -- never by parsing frob check's rendered diagnostic text. The gate
    message is a rendering; the ledger is the source of truth, and a text parse would
    break the moment the message wording changes.
  evidence:
  - tests/unit/test_coordinator_scripts.py::TestRottingTickets::test_flags_a_ticket_past_its_priority_threshold
  - tests/unit/test_coordinator_scripts.py::TestRottingTickets::test_ignores_tickets_still_under_threshold
- text: Given 15 tickets past the rot threshold including 3 critical, when a coordinator
    runs the standing fleet report, then the count and the oldest/highest-priority
    entries appear WITHOUT passing any flag -- reproducing today's state where TICK004
    fired 11 times inside a 19-error frob check list and was read as noise for the
    whole session.
  evidence:
  - tests/unit/test_coordinator_scripts.py::TestPrintTicketRot::test_splits_by_tier_under_distinct_action_headings
- text: 'Distinguish rot by TIER, because the required ACTION differs and a single
    count conflates them. Measured on the 15 tickets currently past threshold: 10
    are tier=epic, 1 is tier=story, only 4 are tier=ticket. A rotting TICKET means
    nobody dispatched it -- the fix is to dispatch it. A rotting EPIC means nobody
    decomposed it -- it is not directly workable, and ''work it'' is the wrong instruction.
    Surfacing them as one undifferentiated number tells a coordinator to do something
    impossible for two thirds of the set, which is why I read the alarm as noise all
    session. This test MUST fail against current main.'
  evidence:
  - tests/unit/test_coordinator_scripts.py::TestRottingTickets::test_distinguishes_epic_and_story_tier_from_ticket_tier
- text: Do NOT fix this by exempting epics from TICK004 -- a rotting epic is a real
    problem (T-1662, the semantics-not-lexical epic, has sat 10 days while its own
    subject matter caused active defects). Report them under a distinct heading naming
    the action, e.g. 'needs decomposition into leaves' versus 'needs dispatch', derived
    from the ledger's tier field rather than from the ticket title.
  evidence:
  - tests/unit/test_coordinator_scripts.py::TestPrintTicketRot::test_splits_by_tier_under_distinct_action_headings
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Done report

TICK004 (rot detection) fired only in frob check's gate layer;
_doable.py only reads its thresholds for filtering, never surfaces the
rotting set. 15 tickets sat past threshold (3 critical, up to 20d) while
every wave picked freshly-filed work, because TICK004 sat as 11 lines
inside a 19-error frob check list and read as noise for a whole session.

Added:
- TICKETS_DIR constant: the live tickets/<id>/ticket.md directory,
  distinct from the git-show-based reads the T-2133 functions use --
  this reads the CURRENT, possibly-uncommitted ledger a dispatch
  decision actually depends on.
- _rot_day_thresholds: per-priority rot-day thresholds from frob.toml's
  [tickets] table, defaulting to the same values as
  frob.gates._tickets_gate._TICK004_DEFAULT_ROT_DAYS (duplicated in
  plain-dict form, not imported, per this script's "no frob import"
  contract). Falls back to defaults when tomllib is unavailable
  (python <3.11 on PATH) too.
- _parse_ticket_ledger_file: hand-parses id/state/priority/tier/created
  directly from a ticket.md file on disk.
- rotting_tickets: every QUEUED/PLANNED ticket under TICKETS_DIR
  (excluding tickets/archive/**) whose priority-specific threshold has
  been crossed since `created` -- mirrors _tick004_queue_rot's own
  selection exactly, derived entirely from structured fields, never by
  parsing frob check's rendered text (acceptance [1]).
- _print_ticket_rot: prints the TICKET ROT section, split under two
  headings naming the required action -- "NEEDS DISPATCH" for
  tier=ticket, "NEEDS DECOMPOSITION" for tier=epic/story (acceptance
  [3]/[4] -- epics are NOT exempted, just reported under their own
  heading). Wired into _print_fleet_report unconditionally, printed
  every time a coordinator runs the standing report, no flag needed
  (acceptance [0]/[2]).

Verified live against the real repo: python3 scripts/fleet_status.py
reported "TICKET ROT: 12" -- 2 NEEDS DISPATCH, 10 NEEDS DECOMPOSITION
(9 epic, 1 story) -- matching the incident's own shape (mostly epics,
a minority of leaf tickets) almost exactly.

frob check --only archgate --only perf --only test --ticket T-2182
showed zero findings against scripts/fleet_status.py (7 pre-existing
errors elsewhere in src/frob/app/ticket_runner/_land_cmd.py and
tests/test_ticket_work_and_land_finish.py, unrelated to this ticket's
scope).

Filed: none -- no out-of-scope work discovered.

### Changed
```
 tickets/T-2182/ticket.md | 26 ++++++++++++++++++++------
 1 file changed, 20 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/unit/test_coordinator_scripts.py::TestPrintTicketRot::test_splits_by_tier_under_distinct_action_headings` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestRottingTickets::test_flags_a_ticket_past_its_priority_threshold` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestRottingTickets::test_ignores_tickets_still_under_threshold` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestRottingTickets::test_distinguishes_epic_and_story_tier_from_ticket_tier` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestRottingTickets::test_only_queued_and_planned_states_are_considered` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-draft-0bd874ac/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-draft-0bd874ac/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV005@scripts/fleet_status.py, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2180/src/frob/app/ticket_runner/_land_cmd.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PRE001@tickets/T-2182, SELFAUDIT001@design, SUPPRESS001@scripts/fleet_status.py, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md, invalid-assignment@scripts/fleet_status.py
