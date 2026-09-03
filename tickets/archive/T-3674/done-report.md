## Done report

Fixed the frob:tests target-form defect in tests/test_tickets_leases.py:
three directives used pytest's `Class::method` collect-only separator
instead of the graph's dotted `Class.method` convention, which fired
DOC007 x3 and the paired DRIFT002 x3. Changed to the dotted form.

Evidence: `timeout 300 uv run frob check --only docanchor` -- DOC007 x3
and DRIFT002 x3 for this file no longer fire. `timeout 300 uv run frob
test --base main` python exit=0.

Deferred (not touched): DRIFT001 at src/frob/process/_derived_lock.py::
_process_already_holds, and DRIFT002 x3 at docs/modules/process.md
(symbols moved to _derived_lock.py in T-3628). docs/modules/process.md
is leased by T-3673 (win32 round 17) so it cannot be edited from this
worktree. Separately, `frob ack` on the DRIFT001 symbol fails with
UnknownRef ("not an edge endpoint") even outside the lease conflict --
needs its own investigation once the doc lease frees. Filed: none (this
is tracked as a known remainder of bucket (a), to be picked up in a
follow-up ticket once T-3673 releases docs/modules/process.md).

### Changed
```
 tests/test_tickets_leases.py  |  6 +++---
 tickets/T-3674/done-report.md | 34 ++++++++++++++++++++++++++++++++++
 tickets/T-3674/ticket.md      | 13 +++++++++++++
 3 files changed, 50 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_tickets_leases.py::TestLeaseShapeValidation::test_read_all_leases_admits_a_windows_style_worktree_path` (pytest node id, verified passing when recorded)
- `tests/test_tickets_leases.py::TestLeaseShapeValidation::test_read_all_leases_still_drops_a_dash_prefixed_windows_style_worktree` (pytest node id, verified passing when recorded)
- `tests/test_tickets_leases.py::TestLeaseShapeValidation::test_worktree_operand_check_admits_windows_paths_directly` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 17 error(s), 4241 warning(s), 896 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tests/test_ci_workflow_matrix.py, COV007@src/frob/strata/_capacity.py, DEPR006@frob-deprecated-baseline.lock.json, DOC006@tickets/T-3673/ticket.md, DRIFT001@src/frob/process/_derived_lock.py, DRIFT002@docs/modules/process.md, LARGE001@src/frob/refactor/_scan.py, LARGE001@src/frob/refactor/_verify.py, OPAQUE001@src/frob/app/_config_external.py, PERF003@src/frob/refactor/_scan.py, PRE001@tickets/T-3674, REF002@src/frob/process/_lock_msvcrt.py, REL001@src/frob/__init__.py, SEC110@tests/ticket_land_suite/test_wip.py, TEST001@src/frob/strata/_models.py, WAIVE011@frob-ratchet.lock.json
