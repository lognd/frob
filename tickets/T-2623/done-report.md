## Done report

### Measurement (the deliverable)

Command: `uv run pytest tests/unit/ -p no:cacheprovider -q -n 4` (reduced
from default `-n auto` after an initial `-n auto` run crashed xdist itself
with an INTERNALERROR under fleet CPU contention -- that run is discarded,
not counted).

Denominator: 18 red of 5237 collected, at main sha 5a15dbd92 (the tip at
measurement time; T-2611's repo-wide renormalization land was deliberately
held off until after this measurement per coordinator instruction).

Exit status 1 (clean pytest completion, no INTERNALERROR, no crashed
worker) on the counted run.

### Exact red-test list, grouped by cause

**Golden export drift (3)** -- filed as T-2630:
- tests/unit/strata/test_export_golden.py::TestExportGolden::test_seccomp
- tests/unit/strata/test_export_golden.py::TestExportGolden::test_k8s
- tests/unit/strata/test_export_golden.py::TestExportGolden::test_iam

**Self-conform / mutation-audit / threat-catalog cluster (6)** -- filed as
T-2634:
- tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant
- tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_repo_unrestricted_scan_is_clean
- tests/unit/strata/test_conform_eval_needle.py::TestEvalNeedleSelfMatch::test_real_repo_design_selfconform_has_no_eval_gap
- tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo::test_every_may_is_load_bearing
- tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo::test_second_detector_gaps_are_exactly_the_disclosed_app_level_kinds
- tests/unit/strata/test_threat.py::TestCaughtByAuditExhaustive::test_every_shipped_entry_has_a_substantive_caught_by

**CLI drift: renumber/land SystemExit + stamp-baseline output string (4)**
-- filed as T-2633 (this is the "renumber-CLI SystemExit" class
the T-2602 fixer mentioned but never enumerated):
- tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_baseline_only_chunk_completes_and_stamps
- tests/unit/test_app_runners_batch7.py::TestTicketRenumber::test_dry_run_without_old_new_exits_1
- tests/unit/test_app_runners_batch7.py::TestTicketRenumber::test_whole_ledger_already_contiguous
- tests/unit/test_app_runners_batch7.py::TestTicketLand::test_land_success_prints_files

**Test-infra staleness (1)** -- filed as T-2637:
- tests/unit/test_conftest_stackdump.py::TestSelfScanHeavyGrouping::test_self_scan_heavy_tests_share_one_xdist_group
  (AttributeError: '_FakeItem' object has no attribute 'get_closest_marker')

**Exports policy residue (1)** -- filed as T-2635:
- tests/unit/test_exports.py::TestFrobExportsPolicyResidue::test_all_nine_packages_report_zero_missing_symbols

**Parse-guard wiring assertion (1)** -- filed as T-2631:
- tests/unit/test_lang_parse_guard.py::TestParseGuardIsWired::test_parse_source_calls_the_guard_helpers

**Mutation sweep queue (1)** -- filed as T-2632:
- tests/unit/test_mutation_sweep_queue.py::TestPendingSweepCount::test_counts_only_pending_entries

**tmLanguage grammar gap (1)** -- filed as T-2636:
- tests/unit/test_strata_tmlanguage.py::test_clause_keywords_covered_by_grammar
  (missing 'exclusive' clause keyword; single-keyword grammar addition,
  low risk, one-directional check by design)

18 tests total, matches the fresh count exactly (the T-2602 fixer's "~19"
estimate included the T-2602 case itself in its own earlier tally; that
one is already fixed on main, hence 18 here, not 19).

### Environment artifacts ruled out

None of the 18 are environment artifacts. `make core`/`frob natives build`
completed cleanly in this worktree before the measurement run (strata_core
and frob_core both built), and the run collected all 5237 tests with zero
collection errors -- no `ModuleNotFoundError: strata_core`/`frob_core`
shapes anywhere in the log. All 18 are real, reproducible test failures
against a fully-built tree.

### Classification

Every one of the 8 groups above needs an actual read-both-sides
investigation to tell "stale fixture" from "genuine product regression"
per test -- none were blanket-classified, and none were fixed, guessed at,
xfailed, skipped, or weakened. Each follow-up ticket body states the
specific hypothesis and explicitly instructs the next agent not to weaken
the guard/detector on the stale-fixture-shaped ones without confirming
which side is wrong first (matching T-2602's precedent: the guard was
correct, the fixture was stale).

### Scope boundary: measurement only, zero repairs (by design)

Zero of the 18 were fixed in this ticket. The coordinator flagged, mid-run,
that T-2611 (a repo-wide `.gitattributes` renormalization touching 6457
tracked files) was waiting to land and needed the fleet drained for a
quiet window -- with instruction to take the measurement now, publish it,
and land without starting further work. This ticket's own scope was
declared empty (`no_scope_declared`) by design (measurement + triage
ticket, not a fix-everything ticket), so filing narrow follow-ups was
always the intended shape of the deliverable, not a shortcut taken under
time pressure.

### Filed

- T-2630 (golden export drift, 3 tests)
- T-2634 (self-conform/mutation-audit/threat cluster, 6 tests)
- T-2633 (CLI SystemExit/output drift, 4 tests)
- T-2637 (conftest stackdump fake-item staleness, 1 test)
- T-2635 (exports policy residue, 1 test)
- T-2631 (parse-guard wiring assertion, 1 test)
- T-2632 (mutation sweep queue, 1 test)
- T-2636 (tmLanguage grammar gap, 1 test)

All 8 drafts renumber to real ids at land per the standard draft mechanism.

### Gates

Evidence: none bound -- no code was fixed in T-2623 itself, so there is no
repair evidence to cite. The published red-test list above (and its
backing log at the measured sha) is the deliverable per the ticket's own
"if you repair none and only file, say so plainly" instruction.

### Changed
```
 tickets/T-2630/ticket.md | 41 ++++++++++++++++++++++++++
 tickets/T-2631/ticket.md | 43 +++++++++++++++++++++++++++
 tickets/T-2632/ticket.md | 37 ++++++++++++++++++++++++
 tickets/T-2633/ticket.md | 51 ++++++++++++++++++++++++++++++++
 tickets/T-2634/ticket.md | 59 ++++++++++++++++++++++++++++++++++++++
 tickets/T-2635/ticket.md | 40 ++++++++++++++++++++++++++
 tickets/T-2636/ticket.md | 42 +++++++++++++++++++++++++++
 tickets/T-2637/ticket.md | 42 +++++++++++++++++++++++++++
 8 files changed, 355 insertions(+)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/gates/_rule_id_scan.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2570/ticket.md, DOC008@docs/modules/gates.md, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, F401@/home/logan/projects/frob/.claude/worktrees/t-2623/src/frob/app/ticket_runner/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2623, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
