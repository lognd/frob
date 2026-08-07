## Done report

Added a worktree-lease guard for the incident named in the ticket: a
dispatched agent's shell ran git merge/make core/frob ticket new
directly against the shared main checkout instead of its own worktree.

Mechanism: FROB_WORKTREE=<abs path> is a dispatcher-set env var naming
the one worktree an agent's shell is authorized to mutate frob's tracked
ticket state in. New frob.tickets.enforce_worktree_lease(root) resolves
root's actual git top-level (repo_root, worktree-correct) and refuses
(Err(WorktreeLeaseViolation)) if FROB_WORKTREE is set and does not match
it. Wired as the first statement of every mutating frob.tickets entry
point: new_ticket, transition (covers start/close/requeue/block/fail),
add_evidence, add_cmd_evidence, set_done_report, record_failure, attach,
archive, renumber, renumber_one. The same guard (mapped to
GateError.WorktreeLeaseViolation) covers frob.gates' stamp_baseline/
stamp_coverage (--stamp-baseline/--stamp-coverage), which also write
tracked repo state. FROB_WORKTREE unset is Ok(None) -- unrestricted --
so the coordinator's own commands (landing worktree changes onto main,
etc.) are unaffected; read-only commands never call this guard.

Defense in depth: frob.scaffold.install_worktree_lease_hook installs
pre-commit + pre-merge-commit git hooks that abort loudly whenever
FROB_AGENT is set non-empty, catching a raw git commit/merge an agent
shell ran directly, independent of whether it went through
frob.tickets at all. Verified end to end with a real git commit under
FROB_AGENT.

Out of scope (noted, not built): `frob release stamp` and `frob ack`
live outside src/frob/{tickets,gates,scaffold}/ (this ticket's declared
scope) and are not yet guarded -- filed as T-draft-0afb5f70.

### Changed
```
 .frob-release.json                            |   9 +-
 CHANGELOG.md                                  |  82 ++++++
 docs/commands/scaffold.md                     |  13 +-
 docs/modules/tickets.md                       | 113 +++++++-
 pyproject.toml                                |   2 +-
 src/frob/app/ticket_runner.py                 | 209 +++++++++++++-
 src/frob/gates/__init__.py                    |  89 +++++-
 src/frob/gates/_baseline.py                   |   4 +
 src/frob/gates/_coverage.py                   |   4 +
 src/frob/gates/_models.py                     |   5 +
 src/frob/scaffold/__init__.py                 |  17 +-
 src/frob/scaffold/project.py                  | 108 ++++++++
 src/frob/tickets/__init__.py                  | 159 +++++++++++
 src/frob/tickets/_land.py                     | 132 ++++++++-
 src/frob/tickets/_models.py                   |  15 ++
 src/frob/tickets/_worktree_guard.py           |  83 ++++++
 tests/test_gates_tickets_hygiene.py           | 105 ++++++++
 tests/test_gates_worktree_lease.py            |  73 +++++
 tests/test_scaffold_worktree_lease_hook.py    | 107 ++++++++
 tests/test_ticket_land.py                     | 167 ++++++++++++
 tests/test_tickets_collision.py               |   8 +-
 tests/test_worktree_guard.py                  | 118 ++++++++
 tests/unit/test_ticket_runner_land_release.py | 182 +++++++++++++
 tests/unit/test_ticket_store.py               | 117 ++++++++
 tickets.md                                    | 374 +++++++++++++++++++++++++-
 uv.lock                                       |   2 +-
 26 files changed, 2268 insertions(+), 29 deletions(-)
```

### Evidence
- `tests/test_worktree_guard.py::TestEnforceWorktreeLease::test_no_env_var_is_unrestricted` (pytest node id, verified passing when recorded)
- `tests/test_worktree_guard.py::TestEnforceWorktreeLease::test_matching_worktree_passes` (pytest node id, verified passing when recorded)
- `tests/test_worktree_guard.py::TestEnforceWorktreeLease::test_mismatched_worktree_refuses` (pytest node id, verified passing when recorded)
- `tests/test_worktree_guard.py::TestEnforceWorktreeLease::test_non_repo_root_passes_through` (pytest node id, verified passing when recorded)
- `tests/test_worktree_guard.py::TestWorktreeGuardWiredIntoMutations::test_new_ticket_from_main_while_leased_elsewhere_fails` (pytest node id, verified passing when recorded)
- `tests/test_worktree_guard.py::TestWorktreeGuardWiredIntoMutations::test_new_ticket_from_leased_worktree_succeeds` (pytest node id, verified passing when recorded)
- `tests/test_worktree_guard.py::TestWorktreeGuardWiredIntoMutations::test_coordinator_with_no_lease_mutates_main_fine` (pytest node id, verified passing when recorded)
- `tests/test_gates_worktree_lease.py::TestStampBaselineWorktreeLease::test_mismatched_lease_refuses` (pytest node id, verified passing when recorded)
- `tests/test_gates_worktree_lease.py::TestStampBaselineWorktreeLease::test_no_lease_succeeds` (pytest node id, verified passing when recorded)
- `tests/test_gates_worktree_lease.py::TestStampCoverageWorktreeLease::test_mismatched_lease_refuses` (pytest node id, verified passing when recorded)
- `tests/test_gates_worktree_lease.py::TestStampCoverageWorktreeLease::test_no_lease_reaches_normal_missing_coverage_error` (pytest node id, verified passing when recorded)
- `tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook::test_installs_pre_commit_and_pre_merge_commit` (pytest node id, verified passing when recorded)
- `tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook::test_refuses_existing_hook_without_force` (pytest node id, verified passing when recorded)
- `tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook::test_not_a_git_repo_fails` (pytest node id, verified passing when recorded)
- `tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook::test_installed_hook_aborts_commit_under_frob_agent` (pytest node id, verified passing when recorded)
- `tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook::test_installed_hook_allows_commit_without_frob_agent` (pytest node id, verified passing when recorded)
