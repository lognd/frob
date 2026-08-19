## Done report

Changed:
- tests/unit/test_app_runners_batch6.py::TestCheckRunner.test_stamp_baseline_only_chunk_completes_and_stamps
- tests/unit/test_app_runners_batch7.py::TestTicketRenumber.test_dry_run_without_old_new_exits_1
- tests/unit/test_app_runners_batch7.py::TestTicketRenumber.test_whole_ledger_already_contiguous
- tests/unit/test_app_runners_batch7.py::TestTicketLand.test_land_success_prints_files

Root cause: THREE unrelated drifts, not one shared cause. All three are
production growing deliberately since these tests were last touched;
production is correct in every case, tests were stale.

1. renumber (2 tests, same cause): T-1882 (a real incident: bare `frob
   ticket renumber` used to perform a whole-ledger bulk rewrite and
   renumbered all 273 tickets in one shot) removed the CLI's ability to
   reach that bulk rewrite for real. `--dry-run` with no <old> <new> is
   now the ONLY surviving no-argument form and is deliberately
   non-fatal (informational, read-only); no-args-no-dry-run now refuses
   outright with SystemExit(1) instead of performing the old bulk
   rewrite. Both tests asserted the pre-T-1882 exit-code shape. Fixed
   by updating both tests' bodies to match the documented T-1882
   behavior, keeping their original names (needed for --check-repro
   identity against the pre-fix parent commit).

2. land (1 test): `_land` (src/frob/app/ticket_runner/_land_cmd.py) now
   runs T-1175/T-1910's `LAND-PROOF:` post-land verification after every
   real (non-dry-run) `land()` call and exits 1 when it does not verify.
   This was added after the test was written; `tmp_path` is not a real
   git repo, so the real `_land_proof_checks` (which shells out to `git
   merge-base --is-ancestor`) genuinely reports not-verified and the
   test's mocked `land()` success read as an overall failure. Fixed by
   also monkeypatching `_land_proof_checks` to report a clean verify,
   matching the sibling `test_land_dry_run_success` case (which never
   reaches this check, since dry-run returns before it).

3. stamp-baseline (1 test): `_stamp_baseline_gate_chunks` chunks
   `--stamp-baseline` runs into `gates-native`/`gates-security`/
   `gates-fast` PLUS a trailing per-gate chunk for any `_ALL_GATES`
   member `_STAGE_GROUPS` does not cover (by its own docstring: this is
   deliberate, so a stage-group drift under-chunks rather than silently
   drops a gate). `_ALL_GATES` has grown ungrouped members since this
   test was written (measured: 3 extra singleton gates today --
   env_var_docs, milestone, root_asset_dirs -- 57/60 group-covered, not
   60/60), so seeding the "already covered" chunk set from just
   gates-native + gates-security no longer equals the complement of
   gates-fast, and the test's completing chunk correctly took the
   "chunk recorded, not yet complete" branch instead of stamping. Fixed
   by deriving the seed as `_ALL_GATES - _STAGE_GROUPS["gates-fast"]`
   directly, so it stays correct regardless of how many ungrouped
   trailing chunks exist.

None of the 4 fixes weakened a guard/detector/production behavior; all
production behavior was confirmed deliberate (T-1882's own docstring for
#1, T-1175/T-1910 LAND-PROOF for #2, `_stamp_baseline_gate_chunks`'s own
docstring for #3) and only the stale test fixtures were changed.

Positive controls: all 4 tests pass after the fix
(tests/unit/test_app_runners_batch6.py::TestCheckRunner and
tests/unit/test_app_runners_batch7.py::TestTicketRenumber/TestTicketLand,
11 collected / 0 failed together with their sibling tests in the same
classes). Deliberately re-broke the renumber fixture's assertion string
and confirmed it fails again (positive control).

Evidence: all 4 bound; each individually confirmed FAILED_AT_PARENT via
`frob ticket evidence T-2633 --check-repro <id>` against parent commit
a36cc9709dce4eb3bf29a15f64c2116a6ed094ec. Formal BUG002 repro designated
as tests/unit/test_app_runners_batch7.py::TestTicketRenumber::test_dry_run_without_old_new_exits_1
(one designated-repro slot per ticket; the other 3 were confirmed via the
same read-only check, not re-designated).

Red-test count: 4 red of 4 in this ticket's scope before fix, 0 red of 11
collected in the touched classes after (TestCheckRunner's one test +
TestTicketRenumber's + TestTicketLand's full classes, all pass).

Filed: none -- all 4 were pre-scoped by T-2633; no additional out-of-scope
issues found.

Gates: uv run frob check --ticket T-2633 --only test -- errors present
are pre-existing repo-wide findings unrelated to the two touched test
files (same 5-error set observed for T-2631: DRIFT001 x3 on unrelated
modules, TEST001 on src/frob/strata/_multifile.py, claude-config-drift).

### Changed
```
 tickets/T-2633/ticket.md | 11 +++++++++--
 1 file changed, 9 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_app_runners_batch7.py::TestTicketRenumber::test_dry_run_without_old_new_exits_1` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketRenumber::test_whole_ledger_already_contiguous` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch7.py::TestTicketLand::test_land_success_prints_files` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_baseline_only_chunk_completes_and_stamps` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/gates/_rule_id_scan.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_milestone.py, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2570/ticket.md, DOC008@docs/modules/gates.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2633, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WAIVE006@src/frob/gates/__init__.py, WAIVE006@src/frob/gates/_coverage.py, WAIVE006@src/frob/gates/_decisions_compliance.py, WAIVE006@src/frob/gates/_doclink_docanchor.py, WAIVE006@src/frob/gates/_mutation_evidence.py, WAIVE006@src/frob/gates/_sys.py, WAIVE006@src/frob/gates/_tickets_gate.py, WAIVE006@src/frob/gates/_todo_fmt.py, WAIVE006@src/frob/tickets/_draft_finalize.py, WAIVE006@src/frob/tickets/_evidence.py, WAIVE006@src/frob/tickets/_models.py, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
