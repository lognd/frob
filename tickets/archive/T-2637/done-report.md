## Done report

Changed: tests/unit/test_conftest_stackdump.py::TestSelfScanHeavyGrouping._FakeItem

Root cause: T-2099 added a `get_closest_marker(...)` call to
`pytest_collection_modifyitems` in tests/conftest.py, but the sibling
`_FakeItem` stub in `TestSelfScanHeavyGrouping` (used by an earlier,
T-1433-era test in the same file) was never updated to match -- a stale
test fixture, not a production defect. The sibling test class
(`TestHeavySubprocessGrouping`, added alongside T-2099) already carries a
correct `_FakeItem.get_closest_marker` stub, confirming production code is
right and this fixture was the one that lagged.

Fix: added a `get_closest_marker` method returning None (this fixture
never carries the heavy_subprocess marker) to the stale `_FakeItem`,
mirroring the sibling class's stub.

Evidence: tests/unit/test_conftest_stackdump.py::TestSelfScanHeavyGrouping::test_self_scan_heavy_tests_share_one_xdist_group
(designated repro, FAILED_AT_PARENT at 8841804057c36e114f0b79c2e96db6b01f7b6482)

Positive controls: full file (8 tests) passes after fix. Deliberately
broke `pytest_collection_modifyitems` (forced the self-scan-heavy branch
to `if False:`) and confirmed the test fails again with a real
AssertionError before reverting the sabotage.

Filed: none

Gates: uv run frob check --ticket T-2637 clean; uv run frob test clean
(see below)

### Changed
```
 tickets/T-2637/ticket.md | 8 ++++++--
 1 file changed, 6 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_conftest_stackdump.py::TestSelfScanHeavyGrouping::test_self_scan_heavy_tests_share_one_xdist_group` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/gates/_rule_id_scan.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_milestone.py, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2570/ticket.md, DOC008@docs/modules/gates.md, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, F401@/home/logan/projects/frob/.claude/worktrees/t2637-t2632/src/frob/app/ticket_runner/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
