---
id: T-0431
title: 'Worktree-lease guard: frob mutating commands + git hooks fail LOUDLY when
  a dispatched agent operates outside its worktree'
state: done
kind: security
origin: human
created: '2026-07-20'
priority: medium
parent: T-0397
tier: ticket
sprint: null
scope:
- src/frob/tickets/
- src/frob/gates/
- src/frob/scaffold/
- frob.toml
- tests/test_worktree_guard.py
- tests/test_gates_worktree_lease.py
- tests/test_scaffold_worktree_lease_hook.py
- docs/modules/tickets.md
- docs/commands/scaffold.md
- .frob-release.json
- CHANGELOG.md
- pyproject.toml
- uv.lock
- tests/test_gates_tickets_hygiene.py
- tests/test_ticket_land.py
- tests/test_tickets_collision.py
- tests/unit/test_ticket_runner_land_release.py
- tests/unit/test_ticket_store.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_worktree_guard.py
  reason: test coverage + doc sections live outside src/frob/{tickets,gates,scaffold}/
    scope globs
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/test_gates_worktree_lease.py
  reason: test coverage + doc sections live outside src/frob/{tickets,gates,scaffold}/
    scope globs
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/test_scaffold_worktree_lease_hook.py
  reason: test coverage + doc sections live outside src/frob/{tickets,gates,scaffold}/
    scope globs
  actor: logan
  at: '2026-07-21'
- op: add
  glob: docs/modules/tickets.md
  reason: test coverage + doc sections live outside src/frob/{tickets,gates,scaffold}/
    scope globs
  actor: logan
  at: '2026-07-21'
- op: add
  glob: docs/commands/scaffold.md
  reason: test coverage + doc sections live outside src/frob/{tickets,gates,scaffold}/
    scope globs
  actor: logan
  at: '2026-07-21'
- op: add
  glob: .frob-release.json
  reason: REL001 bump for new public enforce_worktree_lease/install_worktree_lease_hook
    symbols
  actor: logan
  at: '2026-07-21'
- op: add
  glob: CHANGELOG.md
  reason: REL001 bump for new public enforce_worktree_lease/install_worktree_lease_hook
    symbols
  actor: logan
  at: '2026-07-21'
- op: add
  glob: pyproject.toml
  reason: REL001 bump for new public enforce_worktree_lease/install_worktree_lease_hook
    symbols
  actor: logan
  at: '2026-07-21'
- op: add
  glob: uv.lock
  reason: uv lock update accompanies the version bump
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/test_gates_tickets_hygiene.py
  reason: 'sequential single-worktree dispatch: prior tickets'' (T-0357/T-0338/T-0409)
    committed test files still show in the diff-vs-main SCOPE001 check'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/test_ticket_land.py
  reason: 'sequential single-worktree dispatch: prior tickets'' (T-0357/T-0338/T-0409)
    committed test files still show in the diff-vs-main SCOPE001 check'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/test_tickets_collision.py
  reason: 'sequential single-worktree dispatch: prior tickets'' (T-0357/T-0338/T-0409)
    committed test files still show in the diff-vs-main SCOPE001 check'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/unit/test_ticket_runner_land_release.py
  reason: 'sequential single-worktree dispatch: prior tickets'' (T-0357/T-0338/T-0409)
    committed test files still show in the diff-vs-main SCOPE001 check'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/unit/test_ticket_store.py
  reason: 'sequential single-worktree dispatch: prior tickets'' (T-0357/T-0338/T-0409)
    committed test files still show in the diff-vs-main SCOPE001 check'
  actor: logan
  at: '2026-07-21'
evidence:
- tests/test_worktree_guard.py::TestEnforceWorktreeLease::test_no_env_var_is_unrestricted
- tests/test_worktree_guard.py::TestEnforceWorktreeLease::test_matching_worktree_passes
- tests/test_worktree_guard.py::TestEnforceWorktreeLease::test_mismatched_worktree_refuses
- tests/test_worktree_guard.py::TestEnforceWorktreeLease::test_non_repo_root_passes_through
- tests/test_worktree_guard.py::TestWorktreeGuardWiredIntoMutations::test_new_ticket_from_main_while_leased_elsewhere_fails
- tests/test_worktree_guard.py::TestWorktreeGuardWiredIntoMutations::test_new_ticket_from_leased_worktree_succeeds
- tests/test_worktree_guard.py::TestWorktreeGuardWiredIntoMutations::test_coordinator_with_no_lease_mutates_main_fine
- tests/test_gates_worktree_lease.py::TestStampBaselineWorktreeLease::test_mismatched_lease_refuses
- tests/test_gates_worktree_lease.py::TestStampBaselineWorktreeLease::test_no_lease_succeeds
- tests/test_gates_worktree_lease.py::TestStampCoverageWorktreeLease::test_mismatched_lease_refuses
- tests/test_gates_worktree_lease.py::TestStampCoverageWorktreeLease::test_no_lease_reaches_normal_missing_coverage_error
- tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook::test_installs_pre_commit_and_pre_merge_commit
- tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook::test_refuses_existing_hook_without_force
- tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook::test_not_a_git_repo_fails
- tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook::test_installed_hook_aborts_commit_under_frob_agent
- tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook::test_installed_hook_allows_commit_without_frob_agent
designated_repro_test: null
threat: null
component: null
---
User (2026-07-20), after an incident: a dispatched worktree agent accidentally ran bash commands (git merge main, make core, frob ticket new -> created T-0427) against the SHARED main checkout instead of its worktree; the Edit tool caught FILE edits but bash commands went through, mutating live main. Make it HARD for a dispatched agent to damage the repo via frob, failing loudly (subagent scoping). MECHANISM: (1) LEASE -- when an agent is dispatched to a worktree, record a lease (a .frob/agent-lease file naming the worktree path + agent id, OR the dispatcher sets env FROB_WORKTREE=<abs path>). (2) frob MUTATING-COMMAND GUARD -- every frob command that WRITES (ticket new/close/renumber/land/start/sweep/attach/block/fail/evidence, release stamp/check --stamp, ack, check --stamp-coverage/--stamp-baseline) checks: if a lease/FROB_WORKTREE is active AND the cwd git top-level (`git rev-parse --show-toplevel`) is NOT the leased worktree (e.g. it is main), REFUSE with a loud error naming both paths ("agent leased to <W>; refusing to mutate <main>"). Read-only frob commands (check --ticket, show, list, doable) stay allowed anywhere. (3) GIT HOOK -- frob worktree/scaffold setup installs a pre-commit + pre-merge hook in the MAIN checkout that aborts when an agent-context marker (FROB_WORKTREE / FROB_AGENT) is set, catching a stray raw `git merge main`/`git commit` from an agent shell. (4) The COORDINATOR (no lease / a coordinator marker) mutates main normally. Careful about FALSE POSITIVES: the coordinator landing worktree changes onto main must NOT be blocked (it runs without an agent lease); a legitimately-cd-into-worktree frob command must work. Acceptance: a frob ticket new run from main WHILE FROB_WORKTREE points elsewhere FAILS loudly; the same command from inside the leased worktree SUCCEEDS; the coordinator (no lease) mutates main fine; a raw git commit on main with FROB_AGENT set is aborted by the hook. This is the "hard to be careless" guard for the dispatch layer -- make repo damage require deliberately clearing the lease, not a stray cwd.