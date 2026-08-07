---
id: T-0908
title: in-process system tests leak FROB_WORKTREE into worktree-lease guard
state: done
kind: bug
origin: human
created: '2026-07-26'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/system/test_spawn_budget.py
- tests/system/test_cli_sys_plan.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/system/test_spawn_budget.py::test_ticket_list_spawns_each_argv_at_most_once
- tests/system/test_spawn_budget.py::test_ticket_show_spawns_each_argv_at_most_once
- tests/system/test_spawn_budget.py::test_ticket_doable_spawns_each_argv_at_most_once
- tests/system/test_cli_sys_plan.py::TestSysPlanCli::test_dropped_ticket_is_not_recreated
designated_repro_test: null
threat: null
component: null
---
Found while working T-0880 (system test env leak). Separate from the run()-subprocess
leak T-0880 fixed: several system tests call frob.tickets library functions (new_ticket,
transition, _list/_show/_doable) directly IN-PROCESS against their own tmp_path repo,
so a dispatching agent's FROB_WORKTREE shell env is inherited as-is by the test process
itself (no subprocess boundary to strip it at) and trips the worktree-lease guard
(TicketError.WorktreeLeaseViolation) against the test's own tmp_path, unrelated to the
test's actual correctness:

- tests/system/test_spawn_budget.py (test_ticket_list_spawns_each_argv_at_most_once,
  test_ticket_show_spawns_each_argv_at_most_once,
  test_ticket_doable_spawns_each_argv_at_most_once)
- tests/system/test_cli_sys_plan.py::TestSysPlanCli::test_dropped_ticket_is_not_recreated

Needs its own fix shape (e.g. a fixture/monkeypatch that clears FROB_WORKTREE for
in-process library-call tests), since there is no subprocess env merge to intercept
the way tests/system/conftest.py's run() helper did for T-0880.