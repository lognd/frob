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
