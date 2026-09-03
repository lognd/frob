## Done report

Triaged run 33459475864's 3 ubuntu-only remaining failures against
current main. None reproduce.

1. tests/system/test_cli_check.py::TestCheckPolyglot::
   test_pinned_check_type_reports_skipped_line -- passes standalone
   and inside the full test_cli_check.py file, both with -p no:xdist
   and with xdist. No order-dependence found.

2. tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI
   ::test_force_overrides_the_live_lease_refusal -- passes standalone
   and 3/3 runs of the full file with xdist. No T-3578 signature
   observed in stderr on any run.

3. tests/unit/test_graph_build_lock.py::TestBuildGraphLockScope::
   test_two_processes_never_commit_to_the_same_cache_concurrently --
   passes 3/3 runs against current main, consistent with T-3607 (cache
   rebuild rename-quarantine fix, landed after the measured sha)
   having already fixed this one.

All 3 read as either already fixed upstream of this ticket (test 3,
by T-3607) or transient/order-dependent flakes that did not reproduce
under repeated runs (tests 1 and 2) -- no code change made.

### Changed
```
 tickets/T-3621/ticket.md | 4 ++++
 1 file changed, 4 insertions(+)
```

### Evidence
- `tests/system/test_cli_check.py::TestCheckPolyglot::test_pinned_check_type_reports_skipped_line` (pytest node id, verified passing when recorded)
- `tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI::test_force_overrides_the_live_lease_refusal` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_build_lock.py::TestBuildGraphLockScope::test_two_processes_never_commit_to_the_same_cache_concurrently` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 13 error(s), 4184 warning(s), 900 waived
- error-findings: ARCH102@src/frob/process/_lock.py, ARCH102@src/frob/tickets/_land_squash.py, ARCH103@src/frob/tickets/_leases.py, COV003@tests/test_ci_workflow_matrix.py, COV007@src/frob/strata/_capacity.py, DEPR006@frob-deprecated-baseline.lock.json, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/app/_config_external.py, PRE001@tickets/T-3621, REL001@src/frob/__init__.py, TEST001@src/frob/strata/_models.py, WAIVE011@frob-ratchet.lock.json
