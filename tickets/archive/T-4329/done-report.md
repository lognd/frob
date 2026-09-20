## Done report

Root cause confirmed as documented: tests/system/test_frob_self_model.py's test_checker_fleet_deploy_vet_have_no_undeclared_fs_write_selfaudit001, test_fragments_module_fs_read_is_declared_not_selfaudit001, and test_check_admission_exec_sites_are_declared_not_selfaudit001 all read the session-scoped frob_self_scan_artifacts fixture but were absent from tests/conftest.py's _SELF_SCAN_HEAVY_NAME_SUBSTRINGS, so a real full-repo run could schedule one of them onto a worker other than the one running test_sys_gate_zero_violations, forcing two concurrent full-repo build_graph scans and OOM-killing the workers (win32's memory ceiling) -- corrupting xdist's loadscope bookkeeping into the observed KeyError: <WorkerController gwN> INTERNALERROR abort.

Fix: implemented the ticket's own suggested more-robust option -- pytest_collection_modifyitems now also inspects each item's fixturenames closure for frob_self_scan_artifacts/frob_self_scan_snapshot (the two shared full-repo-scan fixtures) and joins the frob_self_scan_heavy xdist group on that basis, in addition to the existing name-substring list (kept for the older heavy tests that call build_graph/sys_gate directly, not through a shared fixture). Verified directly: a real pytest --collect-only pass over tests/system/test_frob_self_model.py now shows all four self-scan tests (including the three previously-missing ones) carrying the identical {'name': 'frob_self_scan_heavy'} xdist_group marker -- confirmed by inspecting the real marker objects pytest attaches during collection, not just this ticket's own new unit test.

New unit test test_fixture_use_joins_the_heavy_group_without_a_name_listing exercises exactly this: an item with no name-list entry but fixturenames containing frob_self_scan_artifacts/frob_self_scan_snapshot still joins the group. The OTHER bound evidence, test_self_scan_heavy_tests_share_one_xdist_group, is the PRE-EXISTING T-1433 regression test for the substring-list path (unchanged behavior, still passes) -- BUG002 flags it as PASSED-at-parent because it was never meant to demonstrate T-4329's defect; the new fixture-use test is the one that could not have passed before this change (fixturenames was never consulted at all pre-fix).

Filed T-4333 for the broader pattern (hand-maintained membership lists with a derivable-from-usage alternative -- the same shape noted for gate/stage-group registration and waiver-ticket liveness) as a repo-wide survey, out of scope for this single-file ticket.

Scope note: tests/conftest.py carries several OTHER pre-existing frob:tests/frob:doc directives (run_bounded_subprocess, pytest_configure, pytest_sessionfinish, _reset_parse_cache_before_test) unrelated to this fix; their SCOPE002 closure cascades into an unrelated subsystem (src/frob/mutate/*, docs/modules/mutate.md), so scope stayed narrow (tests/conftest.py, tests/unit/test_conftest_stackdump.py -- both actually touched) and frob ticket scope-ack recorded the reasoned exemption instead, per SCOPE002's own documented T-4310 escape hatch.

### Changed
```
 tickets/T-4329/done-report.md      |  24 ++++++++
 tickets/T-4329/ticket.md           | 121 ++++++++++++++++++++++++++++++++++++-
 tickets/T-4333/ticket.md |  70 +++++++++++++++++++++
 3 files changed, 212 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/unit/test_conftest_stackdump.py::TestSelfScanHeavyGrouping::test_self_scan_heavy_tests_share_one_xdist_group` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_stackdump.py::TestSelfScanHeavyGrouping::test_fixture_use_joins_the_heavy_group_without_a_name_listing` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 4686 warning(s), 955 waived
- error-findings: none (measured, zero errors)
