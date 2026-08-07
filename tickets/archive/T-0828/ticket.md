---
id: T-0828
title: 'land: worktree wip/bump commits do not set FROB_LAND_INTERNAL -- pre-commit
  hook deadlocks every land (hit live)'
state: done
kind: bug
origin: agent
created: '2026-07-23'
priority: critical
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land.py
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_ticket_land.py::TestLandInternalEnvThroughHook::test_land_through_changelog_guard_hook_succeeds
- tests/test_ticket_land.py::TestLandInternalEnvThroughHook::test_land_internal_git_env_restores_prior_value
- tests/test_ticket_land.py::TestGitFailureMessageCarriesStderr::test_describe_git_failure_includes_argv_and_stderr
- tests/test_ticket_land.py::TestGitFailureMessageCarriesStderr::test_describe_git_failure_includes_spawn_error
- tests/test_ticket_land.py::TestGitFailureMessageCarriesStderr::test_wip_commit_failure_logs_stderr
designated_repro_test: null
acceptance:
- text: GIVEN the T-0731 pre-commit hook active via core.hooksPath WHEN land creates
    its wip snapshot and bump commits in the worktree THEN those internal commits
    set FROB_LAND_INTERNAL and succeed; a regression test installs the hook in the
    fixture repo and lands through it
  evidence:
  - tests/test_ticket_land.py::TestLandInternalEnvThroughHook::test_land_through_changelog_guard_hook_succeeds
threat: null
component: null
---
Hit live landing T-0594 (2026-07-23): after frob scaffold apply refreshed the hooks, land's worktree wip-snapshot commit was refused by the hook's land-owned CHANGELOG guard -- land sets FROB_LAND_INTERNAL for its main-side commits but not for the worktree wip/bump path, deadlocking every land (GitFailed with the error swallowed; secondary finding: land should surface the failing git command's stderr instead of a bare GitFailed). Coordinator workaround: FROB_LAND_INTERNAL=1 in the invoking env. Fix: set the env on ALL land-internal git commit spawns, and propagate the hook's stderr into the GitFailed error message.