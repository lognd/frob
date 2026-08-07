## Done report

Land-internal git commits (wip snapshot, merge, finalize, squash) now set
FROB_LAND_INTERNAL=1 via a restore-safe context manager, so the T-0731
pre-commit hook's land-owned guards no longer deadlock land; GitFailed
errors now carry the failing argv + stderr. Regression test lands through
a real T-0731-shaped hook installed in the fixture repo.

### Changed
```
 src/frob/tickets/_land.py | 151 ++++++++++++++++++++++++++++++++++++----------
 tests/test_ticket_land.py | 139 ++++++++++++++++++++++++++++++++++++++++++
 tickets.md                |  64 +++++++++++++++++++-
 3 files changed, 319 insertions(+), 35 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestLandInternalEnvThroughHook::test_land_through_changelog_guard_hook_succeeds` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandInternalEnvThroughHook::test_land_internal_git_env_restores_prior_value` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestGitFailureMessageCarriesStderr::test_describe_git_failure_includes_argv_and_stderr` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestGitFailureMessageCarriesStderr::test_describe_git_failure_includes_spawn_error` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestGitFailureMessageCarriesStderr::test_wip_commit_failure_logs_stderr` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 0 error(s), 1129 warning(s), 207 waived
