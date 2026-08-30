## Done report

T-3463: implemented the design T-3399's Description deferred -- rot-check a decomposed epic/story against its OWN children's progress, not just its age. Added _epic_children_all_stalled(t, queue, thresholds, today) in src/frob/gates/_tickets_gate.py: for a decomposed epic (T-2229's is_decomposed), quiet (WARN cap stays, T-3399 behavior unchanged) when any child is IN_PROGRESS or the youngest QUEUED/PLANNED child is still under its own priority's rot threshold; fires (escalates back to ERROR, same age-driven severity as an undecomposed ticket) only when no child is in-progress and even the freshest QUEUED/PLANNED child has itself crossed threshold -- BLOCKED children are excluded from the freshness pool (waiting on something else is not itself rot).

Direct children only: recursive descent through nested grandchild epics is explicitly out of this fix's scope per the ticket's own Description ('needs its own design pass') -- filed T-3476 as the follow-up.

Tests (must-fire + must-stay-quiet), tests/test_tickets_priority.py::TestTick004QueueRot: test_decomposed_epic_with_fresh_queued_child_stays_warn (quiet: one fresh child), test_decomposed_epic_with_all_children_stalled_escalates_to_error (fires: only child is queued and past its own threshold). Pre-existing T-3399 controls (test_decomposed_epic_past_double_threshold_stays_warn_not_error, test_stalled_decomposition_all_children_terminal_still_errors) re-verified green, unaffected.

frob test exceeded the 540s foreground budget; relied on the scoped pytest run (tests/test_tickets_priority.py, 18/18 passed) instead.

Filed: T-3476 (recursive nested-epic descent follow-up).

### Changed
```
 tickets/T-3463/ticket.md           | 21 ++++++++++++++++++++-
 tickets/T-3476/ticket.md | 30 ++++++++++++++++++++++++++++++
 2 files changed, 50 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_tickets_priority.py::TestTick004QueueRot::test_decomposed_epic_with_fresh_queued_child_stays_warn` (pytest node id, verified passing when recorded)
- `tests/test_tickets_priority.py::TestTick004QueueRot::test_decomposed_epic_with_all_children_stalled_escalates_to_error` (pytest node id, verified passing when recorded)
- `tests/test_tickets_priority.py::TestTick004QueueRot::test_decomposed_epic_past_double_threshold_stays_warn_not_error` (pytest node id, verified passing when recorded)
- `tests/test_tickets_priority.py::TestTick004QueueRot::test_stalled_decomposition_all_children_terminal_still_errors` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 15 error(s), 4073 warning(s), 864 waived
- error-findings: COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, LARGE001@.claude/hooks/root-write-guard.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PRE001@tickets/T-3463, REL001@src/frob/__init__.py, SELFAUDIT001@src/frob/gates/_policy_weakening_gate.py, SELFAUDIT001@tests/unit/strata/test_strata_core_gil.py, SELFAUDIT001@tests/unit/test_land_parity_gate.py, SELFAUDIT001@tests/unit/test_sync_claude_config_stale_guard_t3408.py, SELFAUDIT001@tests/unit/verify/test_worker.py, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
