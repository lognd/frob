## Done report

In-process system tests inherited FROB_WORKTREE/FROB_AGENT from a dispatching agent's shell and tripped the worktree-lease guard, since they call frob.tickets library functions directly rather than via subprocess (that path was fixed by T-0880/T-0909). An autouse monkeypatch fixture in tests/system/test_spawn_budget.py and an explicit delenv in test_cli_sys_plan.py::test_dropped_ticket_is_not_recreated now clear both vars for in-process calls. Verified by exporting the lease env in the calling shell and confirming all four affected tests pass.

### Changed
```
 tests/system/test_cli_sys_plan.py | 17 ++++++++++++++--
 tests/system/test_spawn_budget.py | 18 +++++++++++++++++
 tickets.md                        | 42 ++++++++++++++++++++++++++++++++++++++-
 3 files changed, 74 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/system/test_spawn_budget.py::test_ticket_list_spawns_each_argv_at_most_once` (pytest node id, verified passing when recorded)
- `tests/system/test_spawn_budget.py::test_ticket_show_spawns_each_argv_at_most_once` (pytest node id, verified passing when recorded)
- `tests/system/test_spawn_budget.py::test_ticket_doable_spawns_each_argv_at_most_once` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_sys_plan.py::TestSysPlanCli::test_dropped_ticket_is_not_recreated` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
