---
id: T-0909
title: system tests bypassing run() helper still leak FROB_AGENT/FROB_WORKTREE
state: done
kind: bug
origin: human
created: '2026-07-26'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/system/test_cli_check.py
- tests/system/test_cli_ticket.py
- tests/system/conftest.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/system/conftest.py
  reason: run() helper needs a timeout kwarg to preserve the hang-guard when test_cli_ticket.py's
    TestTicketNewNonInteractive routes through it
  actor: logan
  at: '2026-07-26'
evidence:
- tests/system/test_cli_check.py::TestFrobTomlCheckDefaults::test_check_skip_from_frob_toml
- tests/system/test_cli_ticket.py::TestTicketNewNonInteractive::test_new_does_not_prompt_or_hang_without_a_tty
- tests/system/test_run_helper_env_leak.py::TestRunHelperEnvLeak::test_run_strips_dispatch_agent_env_vars
- tests/system/test_run_helper_env_leak.py::TestRunHelperEnvLeak::test_run_explicit_env_can_still_set_frob_agent
designated_repro_test: null
threat: null
component: null
---
Found while working T-0880 (system test env leak fix for tests/system/conftest.py's
run() helper). A dispatching agent's FROB_AGENT/FROB_WORKTREE shell env still leaks
into several system tests that bypass the shared run() helper and call
subprocess.run(FROB + [...]) directly instead:

- tests/system/test_cli_check.py::TestFrobTomlCheckDefaults::test_check_skip_from_frob_toml
- tests/system/test_cli_ticket.py::TestTicketNewNonInteractive::test_new_does_not_prompt_or_hang_without_a_tty

Both fail under FROB_AGENT=1/FROB_WORKTREE=<path> in the dispatching shell (the exact
scenario T-0880 fixed for run()-based tests) because they build their own
subprocess.run(...) call and inherit the full parent environment with no stripping.
Fix: switch these call sites to the shared run() helper (now leak-safe per T-0880),
or apply the same FROB_AGENT/FROB_WORKTREE-stripping to their own subprocess.run call.