## Done report

## Done report

Changed:
src/frob/gitio.py::git_common_dir
src/frob/gitio.py::reset_common_dir_cache
src/frob/gitio.py::common_dir_and_branch
src/frob/tickets/_leases.py::git_common_dir
src/frob/tickets/_leases.py::record_lease
src/frob/tickets/_leases.py::_clear_lease_caches
src/frob/gates/_exclude_hazard.py::_git_common_dir

Design: promoted git_common_dir(root) -> Result[Path, GitError] into
frob.gitio as the single canonical resolver, carrying forward T-0773's
process-lifetime memoization (dict keyed by resolved root) and its
threading.Lock (renamed _common_dir_lock/_common_dir_cache, same shape
as the old _leases.py copy). Added gitio.reset_common_dir_cache() as the
test-only cache-drop hook (_leases._clear_lease_caches now delegates to
it instead of clearing its own dict). frob.tickets._leases.git_common_dir
is now a thin LeaseError-typed wrapper over gitio.git_common_dir;
frob.gates._exclude_hazard._git_common_dir is now a thin Path|None
wrapper over the same. Added gitio.common_dir_and_branch(root) ->
Result[tuple[Path, str], GitError] which spawns ONE
`git rev-parse --git-common-dir --abbrev-ref HEAD` and parses both
result lines; record_lease now calls this instead of its old two
back-to-back spawns (rev-parse --git-common-dir + branch --show-current).

Spawn-budget results: tests/system/test_spawn_budget.py -- 4 passed, 0
xfailed (unchanged from before this ticket).

Dup delta: `frob check --only dup --ticket T-0784` before and after this
change both report 117 duplicate groups (110 waived) -- 0 group-count
delta. The synthetic Result-vs-Path|None git_common_dir/_git_common_dir
pairing from T-0785's dup-scan work (tests/test_dup.py) is a fixture
constructed inline in that test file, independent of the real source
files touched here, so it is unaffected either way.

Evidence:
tests/test_gitio.py::TestGitCommonDir::test_resolves_absolute_common_dir
tests/test_gitio.py::TestGitCommonDir::test_err_when_not_a_repo
tests/test_gitio.py::TestGitCommonDir::test_memoized_per_root
tests/test_gitio.py::TestGitCommonDir::test_reset_clears_cache
tests/test_gitio.py::TestCommonDirAndBranch::test_single_spawn_parses_both_lines
tests/test_gitio.py::TestCommonDirAndBranch::test_err_when_not_a_repo
tests/system/test_spawn_budget.py (4 passed 0 xfailed)
tests/test_tickets_leases.py (all passing)
tests/test_ticket_leases_cross_worktree.py (all passing)
tests/test_gates.py::TestExcludeHazardGate::* (all passing)

Filed: none

Gates: `frob check --ticket T-0784` chunked loop (lint/static/gates-fast/
gates-native/gates-security) clean except REL001 (public API version
bump), which is land-owned per docs/guides/agent-playbook.md section 4b
and left for `frob ticket land` -- FROB_AGENT was not set in this shell
so the usual worktree-agent suppression did not apply, but no version/
changelog/lockfile edit was made by hand. PRE001 cleared via
`frob ticket sweep T-0784` after the code changes landed. `frob test
--base main` (touched-set): python exit=0.

Deviations: none from the ticket's plan. One correction made mid-flight:
the frob:tests directive I first wrote for common_dir_and_branch used
`Class::method` (double-colon) instead of the repo's `path::Class.method`
dot-separator convention, which DRIFT002 caught immediately (dangling
tests edge, no candidates) -- fixed to match the convention used
everywhere else in this file.

### Changed
(no changed files detected)

### Evidence
- `tests/test_gitio.py::TestGitCommonDir::test_resolves_absolute_common_dir` (pytest node id, verified passing when recorded)
- `tests/test_gitio.py::TestGitCommonDir::test_err_when_not_a_repo` (pytest node id, verified passing when recorded)
- `tests/test_gitio.py::TestGitCommonDir::test_memoized_per_root` (pytest node id, verified passing when recorded)
- `tests/test_gitio.py::TestGitCommonDir::test_reset_clears_cache` (pytest node id, verified passing when recorded)
- `tests/test_gitio.py::TestCommonDirAndBranch::test_single_spawn_parses_both_lines` (pytest node id, verified passing when recorded)
- `tests/test_gitio.py::TestCommonDirAndBranch::test_err_when_not_a_repo` (pytest node id, verified passing when recorded)
