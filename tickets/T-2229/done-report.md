## Done report

Changed:
  src/frob/gates/_tickets_gate.py::_has_active_child (new)
  src/frob/gates/_tickets_gate.py::_tick004_queue_rot (message-selection branch)
  scripts/fleet_status.py::_parse_ticket_ledger_file (parent field extraction)
  scripts/fleet_status.py::_epics_with_active_children (new)
  scripts/fleet_status.py::rotting_tickets (has_active_child field)
  scripts/fleet_status.py::_print_ticket_rot (DECOMPOSED, BEING WORKED bucket)
  docs/guides/coordinator-scripts.md (new/updated entries)

Read `parent` as a STRUCTURED field off each candidate CHILD ticket
record in both the gate (`Ticket.parent`, pydantic model) and the script
(`_parse_ticket_ledger_file`'s own flat-line parser, matching its
existing "no `import yaml`" contract) -- never inferred from title text
or a hand-authored epic-id allowlist, per the ticket's explicit
instruction. Only an epic/story with at least one NON-TERMINAL child
(state not done/dropped) gets the distinct message/bucket; a genuinely
undecomposed epic/story (no children at all) and one whose only child is
terminal both still rot under the ordinary message -- covered by two
separate must-still-pass tests in both the gate and the script.

Evidence: tests/test_tickets_priority.py::TestTick004QueueRot::test_decomposed_epic_gets_a_distinct_message_not_work_it
  (repro, gate side)
  tests/unit/test_coordinator_scripts.py::TestPrintTicketRot::test_decomposed_epic_prints_under_its_own_heading_not_needs_decomposition
  (script side)
  Both FAILED_AT_PARENT confirmed at f175ba1d4 (repro-only commit);
  PASSED after the fix commit 00d32a576.
  Also added: test_epic_with_active_child_is_flagged_has_active_child,
  test_epic_with_no_children_at_all_is_not_flagged (must-still-pass),
  test_epic_whose_only_child_is_terminal_is_not_flagged (must-still-pass),
  test_undecomposed_epic_with_no_children_still_gets_work_it (gate-side
  must-still-pass), test_epic_whose_only_child_is_terminal_still_gets_work_it
  (gate-side must-still-pass).
  Full runs: tests/unit/test_coordinator_scripts.py + tests/test_tickets_priority.py
  -- 108 collected, 0 failed.
  Manually verified `frob check --only tickets` (gate) and
  `uv run python3 scripts/fleet_status.py` (script) against this repo's
  real live ticket data (T-1623-shape) agree exactly: T-0969/T-1273
  (epics with in-progress children in the real ledger) get the new
  message/bucket, T-1135/T-1136/T-1137/T-1219/T-1238/T-1599 (genuinely
  undecomposed) keep the ordinary one.

Filed: none

Gates: frob check --ticket T-2229 -- gate:SCOPE/gate:PREWORK clean;
  gate:AFFECT closed via real docs/guides/coordinator-scripts.md edits
  (not waived) for all 4 touched public symbols; no other gate family's
  counts changed by this diff (all repo-wide per the check's own
  scope-note).

### Changed
```
 docs/guides/coordinator-scripts.md     |  54 ++++++++++++-----
 scripts/fleet_status.py                |  91 ++++++++++++++++++++++++++--
 src/frob/gates/_tickets_gate.py        |  41 ++++++++++++-
 tests/test_tickets_priority.py         |  81 ++++++++++++++++++++++++-
 tests/unit/test_coordinator_scripts.py | 107 ++++++++++++++++++++++++++++++++-
 tickets/T-2229/ticket.md               |  24 +++++++-
 6 files changed, 371 insertions(+), 27 deletions(-)
```

### Evidence
- `tests/test_tickets_priority.py::TestTick004QueueRot::test_decomposed_epic_gets_a_distinct_message_not_work_it` (pytest node id, verified passing when recorded)
- `tests/unit/test_coordinator_scripts.py::TestPrintTicketRot::test_decomposed_epic_prints_under_its_own_heading_not_needs_decomposition` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@scripts/fleet_status.py, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/scaffold/_skills_sync.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, DOC001@docs/commands/release.md, DOC002@src/frob/scaffold/_skills_sync.py, DOC005@README.md, DOC005@docs/modules/cli.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2229/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2229/src/frob/gates/_tickets_gate.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2229/src/frob/lang/_nodes.py, F541@/home/logan/projects/frob/.claude/worktrees/t-2229/tests/test_ticket_work_and_land_finish.py, PERF004@scripts/fleet_status.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, RENDER001@src/frob/release/_cli.py, RENDER001@src/frob/scaffold/_skills_sync.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
