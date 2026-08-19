## Done report

Changed:
  docs/modules/app.md (cycle_runner.run bullet)
  src/frob/app/cycle_runner.py (removed stale AFFECT001 waiver, added frob:tests edge)
  tests/unit/test_cycle_runner_doc_waiver_t2598.py (new repro test)

Evidence:
  tests/unit/test_cycle_runner_doc_waiver_t2598.py::TestCycleRunnerDocWaiver::test_app_doc_describes_current_cycle_runner_contract (designated repro, FAILED_AT_PARENT verified against 1ff6b9619)
  tests/unit/test_cycle_runner_doc_waiver_t2598.py::TestCycleRunnerDocWaiver::test_affect001_waiver_removed_arch103_waiver_kept

Filed: none

Gates: frob check --only affect_drift --ticket T-2598 clean (gate:affect_drift 0 findings,
FROB_NO_GATE_CACHE=1 verified). Pre-existing repo-wide DRIFT001 (x2) and CLAUDE001 findings
are unrelated to this ticket's scope (docs/modules/app.md, src/frob/app/cycle_runner.py) and
predate this change.

The general point from the ticket: a waiver reason that promises a follow-up ticket is only
as good as the ticket. Consider whether WAIVE001/a new check should require a real ticket id
in any waiver reason that names future work, rather than prose alone -- filing this as a
follow-up rather than widening this ticket's own scope.

### Changed
```
 docs/modules/app.md                              | 11 +++++-
 src/frob/app/cycle_runner.py                     |  6 +--
 tests/unit/test_cycle_runner_doc_waiver_t2598.py | 49 ++++++++++++++++++++++++
 tickets/T-2598/ticket.md                         |  7 +++-
 tickets/T-draft-178e56ed/ticket.md               | 36 +++++++++++++++++
 5 files changed, 102 insertions(+), 7 deletions(-)
```

### Evidence
- `tests/unit/test_cycle_runner_doc_waiver_t2598.py::TestCycleRunnerDocWaiver::test_app_doc_describes_current_cycle_runner_contract` (pytest node id, verified passing when recorded)
- `tests/unit/test_cycle_runner_doc_waiver_t2598.py::TestCycleRunnerDocWaiver::test_affect001_waiver_removed_arch103_waiver_kept` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/gates/_rule_id_scan.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2570/ticket.md, DOC006@tickets/T-2585/ticket.md, DOC008@docs/modules/gates.md, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2598/src/frob/app/ticket_runner/_ledger_mirror.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2598/src/frob/scaffold/project.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2598, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
