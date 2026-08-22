## Done report

Changed:
- src/frob/tickets/_flow.py (new) -- sprint_view, sprint_velocity, ticket_flow, _tickets_committed_to, _STATE_LINE_RE, _ticket_state_in_blob, _ledger_commit_history, _blob_at, _mine_done_transitions[_v1/_v2], _FLOW_TRAILING_DAYS, _load_flow_ticket_universe, _count_filed_by_day, _count_landed_by_day, _build_flow_rows, _median_cycle_days -- verbatim move out of _setters.py, directives intact
- src/frob/tickets/_setters.py -- flow family removed; re-imports/re-exports sprint_velocity/sprint_view/ticket_flow from _flow so frob.tickets.__init__'s existing import line needs no change; dropped now-unused imports (re, Sequence, datetime, timedelta, SprintReport, SprintTransition, SprintVelocityReport, TicketFlowReport, TicketFlowRow, TicketState, v2_state_transitions, TicketQueue); dropped the now-inapplicable LARGE001 waiver header
- tests/test_tickets_velocity.py -- retargeted frob:tests directives for sprint_velocity/ticket_flow/_median_cycle_days to _flow.py; retargeted a plain import of _mine_done_transitions_v1/_v2 from _setters to _flow (no mock.patch call sites target the moved names -- verified via git grep); added frob:ticket T-2834 to every test function/class COV002 flagged as touched-with-no-open-ticket-edge
- tests/test_tickets_tiers.py -- retargeted the frob:tests directive for sprint_view to _flow.py; added frob:ticket T-2834 to the COV002-flagged class/test

Seam verification: confirmed on inspection -- the flow family (~470 lines) shares no ledger-write substrate with the setter family; its only coupling to _setters.py was `_store_mode`/`load_archive` (also used independently by `_ticket_currently_archived`, kept in _setters.py) and ordinary `date`/`Path` imports. This is a real, distinct consumer concern (git-history mining across the whole queue for burn-down/velocity reporting) vs. the setters' single-ticket field mutation -- not a forced line-count split.

frob.tickets.__init__ re-export path: verified unaffected -- __init__.py's `from frob.tickets._setters import (sprint_velocity, sprint_view, ticket_flow)` still resolves because _setters.py re-imports and re-exports those three names from _flow.py. `python -c "import frob.tickets as t; t.sprint_view, t.sprint_velocity, t.ticket_flow"` resolves cleanly, no __init__.py edit needed (matches T-2834's own noted premise).

Evidence: tests/test_tickets_velocity.py::TestSprintVelocity::test_transitions_mined_from_history, tests/test_tickets_tiers.py::TestSprintShow::test_state_rollup_and_velocity, tests/test_tickets_velocity.py::TestTicketFlow::test_filed_and_landed_counted_per_day, tests/test_tickets_velocity.py::TestSprintVelocityV2Mode::test_v1_v2_parity_for_equivalent_history

Filed: none

Gates: `frob check --ticket T-2834` -- every finding this split itself introduced (F401 unused TicketQueue import, ty stale-import errors, DRIFT002 doc/test-edge moves, COV002 missing frob:ticket edges on touched tests) is fixed; final scoped run shows zero remaining errors touching _setters.py/_flow.py/the two retargeted test files. Remaining errors in that run (SYS003 on src/frob/check/__init__.py, an unrelated import-cycle report, ruff/DRIFT/DOC/TICK/SEC findings elsewhere) are pre-existing repo baseline noise -- confirmed by running the same checks against unmodified main for the affected identities (e.g. tests/test_ticket_leases.py's pre-existing `--reason` dispatch-table failures reproduce byte-for-byte on main with none of this ticket's changes present). Unscoped `frob check` (no --ticket) shows only the expected PRE001/SCOPE001 "no --ticket passed" notices touching the two changed files, no new defects. `uv run pytest -q tests/test_tickets_velocity.py tests/test_tickets_tiers.py tests/test_worktree_guard.py tests/unit/test_rapid_sweep.py` -> SUITE-RESULT: exitstatus=0 collected=213 failed=0.

### Changed
```
 tickets/T-2834/done-report.md | 34 ++++++++++++++++++++++++++++++++++
 tickets/T-2834/ticket.md      | 10 +++++++++-
 2 files changed, 43 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_tickets_velocity.py::TestSprintVelocity::test_transitions_mined_from_history` (pytest node id, verified passing when recorded)
- `tests/test_tickets_tiers.py::TestSprintShow::test_state_rollup_and_velocity` (pytest node id, verified passing when recorded)
- `tests/test_tickets_velocity.py::TestTicketFlow::test_filed_and_landed_counted_per_day` (pytest node id, verified passing when recorded)
- `tests/test_tickets_velocity.py::TestSprintVelocityV2Mode::test_v1_v2_parity_for_equivalent_history` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 31 error(s), 627 warning(s), 743 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, CYCLE001@src/frob/__init__.py, DOC006@docs/audits/test005-zero-classification-t1418.md, DOC011@docs/investigations/T-2796-backlog-reproduction.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, DSL001@src/frob/arch/_patterns.py, E501@/home/logan/projects/frob/.claude/worktrees/t2833-t2834/src/frob/strata/_selfconform_core_rules.py, E501@/home/logan/projects/frob/.claude/worktrees/t2833-t2834/src/frob/strata/_selfconform_kinds.py, I001@/home/logan/projects/frob/.claude/worktrees/t2833-t2834/src/frob/strata/_selfconform.py, I001@/home/logan/projects/frob/.claude/worktrees/t2833-t2834/src/frob/strata/_selfconform_binding_rules.py, I001@/home/logan/projects/frob/.claude/worktrees/t2833-t2834/src/frob/strata/_selfconform_core_rules.py, I001@/home/logan/projects/frob/.claude/worktrees/t2833-t2834/src/frob/strata/_selfconform_kinds.py, I001@/home/logan/projects/frob/.claude/worktrees/t2833-t2834/src/frob/strata/_selfconform_models.py, I001@/home/logan/projects/frob/.claude/worktrees/t2833-t2834/src/frob/strata/_selfconform_surface_rules.py, PERF004@src/frob/strata/_selfconform_binding_rules.py, PERF004@src/frob/strata/_selfconform_surface_rules.py, PERF004@src/frob/tickets/_evidence.py, PRE001@tickets/T-2834, REG002@docs/design/registry/check-coverage.yaml, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md
