## Done report

Review fold (REJECT -> addressed, one commit):

R1 (required): scope-added tests/unit/test_scaffold_managed.py ("R1:
test_clean_after_apply's block-count arithmetic must account for the
new T-0574 stash-guard block"). Exposed the stash guard's hook name(s)
as a public STASH_GUARD_HOOK_NAMES tuple in _managed.py (same shape as
MANAGED_HOOK_NAMES) instead of a magic +1, and used it in
test_clean_after_apply's expected_count. Verified the test was actually
red before the fix and green after.

M2: added TestStashGuardBlock with the two missing precedent-mirroring
cases: test_refuses_to_clobber_foreign_reference_transaction_hook and
test_stale_ours_stash_guard_hook_is_updated, both bound via frob:tests
on _stash_guard_status/_apply_stash_guard.

M1: scope-added docs/commands/scaffold.md ("M1: document the T-0574
stash-guard hook block alongside the other managed blocks") and added a
bullet in the Managed blocks (T-0736) section explaining why it is its
own hook (alias.stash is silently ignored by git; pre-commit never
fires for stash) and its git>=2.28 requirement.

M3: frob agent env now shlex.quote()s each exported value before
printing, so a worktree path containing a space/quote/shell
metacharacter cannot break eval "$(frob agent env)". Updated the two
tests that asserted the literal export line to build the expected
string via shlex.quote instead of a hardcoded double-quote form.

M5: added a one-line git>=2.28 note to README.md's Setup section: the
reference-transaction hook is still written on an older git, but git
itself never invokes that hook name below 2.28, so the guard is
silently inert -- fail-open, not an install error.

Verification: uv run --frozen pytest tests/unit/test_scaffold_managed.py
tests/test_worktree_guard.py -q -> 23 passed (7 + 16), all 23 collect
cleanly and match this ticket's frob:tests directives. uv run --frozen
frob check --ticket T-0574 --only gates-fast -> gate:DOC 0 errors (was
2), gate-summary 0 errors, 1093 warnings, 158 waived (all pre-existing,
none new).

### Changed
```
 README.md                           |   3 +-
 docs/guides/agent-playbook.md       |  28 ++++++
 docs/modules/app.md                 |   6 ++
 src/frob/__main__.py                |  30 ++++++
 src/frob/app/agent_runner.py        |  89 ++++++++++++++++++
 src/frob/scaffold/_managed.py       | 160 ++++++++++++++++++++++++++++++-
 src/frob/tickets/_worktree_guard.py |  39 +++++++-
 tests/test_worktree_guard.py        | 132 +++++++++++++++++++++++++-
 tickets.md                          | 181 +++++++++++++++++++++++++++++++++++-
 9 files changed, 660 insertions(+), 8 deletions(-)
```

### Evidence
- `tests/test_worktree_guard.py::TestAgentEnvExports::test_resolves_worktree_root` (pytest node id, verified passing when recorded)
- `tests/test_worktree_guard.py::TestAgentEnvExports::test_non_repo_root_errs` (pytest node id, verified passing when recorded)
- `tests/test_worktree_guard.py::TestAgentRunnerEnv::test_env_prints_export_lines_for_worktree` (pytest node id, verified passing when recorded)
- `tests/test_worktree_guard.py::TestAgentRunnerEnv::test_env_defaults_to_cwd` (pytest node id, verified passing when recorded)
- `tests/test_worktree_guard.py::TestAgentRunnerEnv::test_env_non_repo_path_exits_nonzero` (pytest node id, verified passing when recorded)
- `tests/test_worktree_guard.py::TestStashGuardHook::test_refuses_stash_while_sibling_worktree_exists` (pytest node id, verified passing when recorded)
- `tests/test_worktree_guard.py::TestStashGuardHook::test_allows_stash_with_no_sibling_worktree` (pytest node id, verified passing when recorded)
- `tests/test_worktree_guard.py::TestStashGuardHook::test_commit_is_unaffected_by_the_hook` (pytest node id, verified passing when recorded)
- `tests/test_worktree_guard.py::TestStashGuardHook::test_idempotent_second_apply_is_noop` (pytest node id, verified passing when recorded)
- `tests/unit/test_scaffold_managed.py::TestStashGuardBlock::test_refuses_to_clobber_foreign_reference_transaction_hook` (pytest node id, verified passing when recorded)
- `tests/unit/test_scaffold_managed.py::TestStashGuardBlock::test_stale_ours_stash_guard_hook_is_updated` (pytest node id, verified passing when recorded)
- `tests/unit/test_scaffold_managed.py::TestScaffoldConformanceStatus::test_clean_after_apply` (pytest node id, verified passing when recorded)
