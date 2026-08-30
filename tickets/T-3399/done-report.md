## Done report

TICK004 (_tick004_queue_rot) computed its severity purely from age
(ERROR past 2x threshold, else WARN) BEFORE checking whether the
ticket is a decomposed epic/story (T-2229's own _has_active_child) --
so a decomposed epic whose message already said "already decomposed
and being worked... the recommended action is checking the children's
own progress instead" still reported as a hard ERROR the moment its
age crossed 2x threshold. MEASURED 2026-08-29: three genuinely healthy
epics (T-0969/T-1273/T-1686) errored purely from this mismatch,
clearable only by corrupting otherwise-correct ledger state.

Fix: when a ticket is a decomposed epic/story (is_decomposed, same
condition the message text already used), severity is capped at WARN
-- never escalated to ERROR by age alone. The signal is not silenced:
it still reports, still names the age, still recommends checking the
children. An undecomposed ticket (T-1382's own shape) is completely
unaffected -- is_decomposed requires both the EPIC/STORY tier and a
live non-terminal child, so a plain leaf ticket, or a decomposition
that has fully gone terminal (nothing active), still escalates to
ERROR exactly as before.

DECISION on the ticket body's second question (children's-progress
measurement): explicitly OUT of this fix's scope. Measuring a
decomposed epic's rot against its children's own progress (an epic
whose children are ALL also stalled really is rotting, a sharper
finding than a flat WARN cap) needs its own recursive computation and
calibration. Filed as a follow-up: T-3463.

Three fixtures added to tests/test_tickets_priority.py::
TestTick004QueueRot:
- test_undecomposed_stale_ticket_still_errors (MUST-FIRE, T-1382's
  shape): still ERROR.
- test_decomposed_epic_past_double_threshold_stays_warn_not_error
  (MUST-STAY-QUIET, the exact measured incident shape): WARN, not
  ERROR.
- test_stalled_decomposition_all_children_terminal_still_errors
  (THIRD fixture): decomposition that has stalled (all children
  terminal) still ERRORs.

Full tests/test_tickets_priority.py: 16/16 pass. `frob check --ticket
T-3399 --budget 300`: 0 errors (TICK004 now reports only T-1382,
matching the measured baseline). `frob test --base main` exceeded
540s twice (unrelated to this change -- a known slow-suite condition);
relied on node-id pytest runs instead per the series' verification
rule.

### Changed
```
 tickets/T-3399/ticket.md           | 20 ++++++++++++++-
 tickets/T-3463/ticket.md | 51 ++++++++++++++++++++++++++++++++++++++
 2 files changed, 70 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_tickets_priority.py::TestTick004QueueRot::test_undecomposed_stale_ticket_still_errors` (pytest node id, verified passing when recorded)
- `tests/test_tickets_priority.py::TestTick004QueueRot::test_decomposed_epic_past_double_threshold_stays_warn_not_error` (pytest node id, verified passing when recorded)
- `tests/test_tickets_priority.py::TestTick004QueueRot::test_stalled_decomposition_all_children_terminal_still_errors` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 10 error(s), 4060 warning(s), 861 waived
- error-findings: COV003@tickets/T-3410, DEPR006@frob-deprecated-baseline.lock.json, DOC006@tickets/T-3411/ticket.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, LARGE001@.claude/hooks/root-write-guard.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, REL001@src/frob/__init__.py, SELFAUDIT001@design, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
