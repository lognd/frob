---
id: T-0880
title: 'system test env leak: FROB_AGENT/FROB_WORKTREE prefix breaks tests/system/**
  subprocess verification'
state: done
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/system/conftest.py
- docs/guides/agent-playbook.md
- tests/system/test_run_helper_env_leak.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/system/test_run_helper_env_leak.py
  reason: 'The SYS100 eval/exec needle the ticket describes is implemented in

    src/frob/vet/_capability.py''s plain-substring needle table (scan_file_capabilities),

    not in src/frob/strata/**. The strata self-conform scan (_selfconform.py) only

    calls into that shared vet scanner; there is no independent eval/exec needle

    inside strata itself. Fixing the false positive requires the same word-boundary

    treatment vet/_capability.py already uses for compile(/napi (T-0151/T-0019

    precedents), so this adds src/frob/vet/_capability.py to scope.

    '
  actor: logan
  at: '2026-07-26'
evidence:
- tests/system/test_run_helper_env_leak.py::TestRunHelperEnvLeak::test_run_strips_dispatch_agent_env_vars
- tests/system/test_run_helper_env_leak.py::TestRunHelperEnvLeak::test_run_explicit_env_can_still_set_frob_agent
designated_repro_test: null
threat: null
component: null
---
Setting FROB_AGENT=1/FROB_WORKTREE=<path> in the shell env before running
`frob ticket evidence`/`frob test` (as the agent-playbook and dispatch
prompts instruct for every frob invocation) leaks into any system test's
own `run()` helper (tests/system/conftest.py, `os.environ | env`), which
spawns the real `frob` CLI as a subprocess -- so a system test that calls
`run("check", ...)` unscoped inherits FROB_AGENT and gets the T-0627
bare-check refusal, and a test that runs `frob check`/`stamp-coverage`
against its own `tmp_path` inherits FROB_WORKTREE and trips T-0836's
worktree-lease guard (cwd != leased worktree) -- both spurious, unrelated
to the test's actual correctness. Reproduced directly (T-0750 dispatch):

    FROB_AGENT=1 FROB_WORKTREE=<worktree> uv run frob ticket evidence \
      T-0750 tests/system/test_cli_check.py::TestCheckCleanProject::test_clean_code_exits_zero
    -> python verification run FAILED (run_selected: python exit=1)

    # same node id, bare invocation, no env leak:
    uv run frob ticket evidence T-0750 tests/system/test_cli_check.py::...
    -> passes, evidence recorded

This affects every dispatched worktree agent trying to record evidence or
run `frob test` against tests/system/**: the playbook's own mandated
env-var prefix actively breaks verification of the test suite it exists to
protect. Needs either (a) `tests/system/conftest.py`'s `run()` helper to
strip FROB_AGENT/FROB_WORKTREE before merging env (system tests exercise
`frob` as an end user would, never as a dispatched agent), or (b)
explicit playbook guidance that evidence-recording/pytest invocations
must NOT carry the FROB_AGENT/FROB_WORKTREE prefix (only `frob
check`/`frob ticket` gate commands need it). Filed here rather than fixed
silently since tests/system/conftest.py is out of my ticket's own scope
list for this dispatch in one case (T-0742) and touching the playbook
docs is a different kind of change than either of my two tickets.