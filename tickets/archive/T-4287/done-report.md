## Done report

The land-time sibling-state-regression guard (T-1914) refused a land whenever
a sibling ticket's rank dropped across the merge, with no way to tell an
accidental hand-resolved-merge resurrection apart from a deliberate,
audited `frob ticket reopen --reason TEXT`. Fixed by recognizing the
reopen verb's own audit trail: `_reopen_log_entries` reads a ticket's
"## Reopen log" section, `_sibling_reopen_log_signatures` snapshots it
per sibling before and after the merge (mirroring the existing pre/post
state snapshot), and `_regression_is_audited_reopen`/
`_assert_no_sibling_state_regression` exclude a rank-drop from refusal
only when the sibling gained a NEW reopen-log entry across the merge --
exactly the shape a `frob ticket reopen` on main leaves behind. A hand
resurrection with no reopen-log entry is refused exactly as before
(AC2), proven by `test_hand_resurrection_without_reopen_log_is_still_
refused`.

AC3: `reopen_ticket` now calls `_worktrees_carrying_terminal_copy`
before performing the DONE -> QUEUED transition, logging a WARNING
naming every live cross-worktree lease whose own on-disk copy of the
ticket is still terminal -- the surprise the filer measured directly is
now a disclosed decision point instead of a blocked land discovered
later.

Scope widened (recorded via `frob ticket scope --add`) to
`_reporting.py` (AC3 lives in `reopen_ticket`, not `_land.py`), the two
test files carrying the new evidence, and `docs/modules/tickets.md`
(AFFECT001 doc-drift on the changed `reopen_ticket` docstring's
affects()-closure). `frob ticket scope-ack` records why _land.py's own
pre-existing, unrelated scope-closure breadth (dozens of private-helper
edges into sibling _land_*.py modules, already T-1651/LARGE001/ARCH102-
documented) was not chased down as part of this fix.

### Changed
```
 tickets/T-4287/ticket.md | 69 +++++++++++++++++++++++++++++++++++++++++++-----
 1 file changed, 63 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/unit/test_land_sibling_regression.py::TestAuditedReopenEscape::test_audited_reopen_is_not_flagged_as_regression` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_sibling_regression.py::TestAuditedReopenEscape::test_hand_resurrection_without_reopen_log_is_still_refused` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_sibling_regression.py::TestNamesStrandedWorktreesBeforeReopen::test_worktrees_carrying_terminal_copy_are_named` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 5 error(s), 4635 warning(s), 946 waived
- error-findings: COV007@src/frob/gates/_tdd_order.py, PRE001@tickets/T-4287, SCOPE002@tickets.md, SELFAUDIT001@design, WIRE002@tests/test_ci_workflow_timeout.py
