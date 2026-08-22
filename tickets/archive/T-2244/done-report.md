## Done report

Repointed the Makefile's `format:`/`lint:`/`lint-fix:`/`typecheck:`/
`test:`/`test-unit:`/`test-integration:`/`test-system:` targets at
frob subcommands, per T-1382's standing "workflows belong in frob
subcommands, not GNU-make recipes" directive.

`format:` -> `frob format --select-imports-only`; `lint-fix:` ->
`frob format` (both new in this series via T-2251, which this ticket
depends on landing first). `lint:` -> `frob check --only ruff
--skip-ruff-format --only ty` -- deliberately kept lint-only (no
`ruff format --check` stage), preserving the exact scope `lint:` had
before this change; bundling format-check in would newly fail on the
~180 pre-existing files T-2359 (still open) has not yet reformatted,
which acceptance[2] forbids. `typecheck:` -> `frob check --only ty`.

`test:`/`test-unit:`/`test-integration:`/`test-system:` -> `frob test
[PATH]`, using T-2319's directory-scoped SELECTION (`frob test PATH`
matches `pytest PATH`'s subset semantics). `-n auto --dist=loadgroup`
is not repeated in the Makefile recipes -- confirmed it is already
baked into pyproject.toml's `[tool.pytest.ini_options] addopts`, so
every pytest invocation gets it automatically regardless of caller.
`test-fast:` stays on raw `pytest --testmon` -- no `frob test`
equivalent to `--testmon`'s incremental-rerun mode exists today,
disclosed gap per this ticket's own body, not an oversight.

Amended acceptance[0]/[1]'s stale text (it named `frob fmt`/`frob
quality check`/`frob quality test`, which this ticket's own 2026-08-16/
2026-08-18 Failure log entries already found broken/inadequate) to
match the commands actually used.

Tests: extended the existing `tests/unit/test_makefile_coverage.py`
(reused its `_recipe_body` helper -- no new file, no duplicated
Makefile-parsing logic) with 9 new cases pinning each repointed
recipe's exact delegation target. All pass; evidence bound to
acceptance[0]/[1].

Acceptance[2] (no strictness regression) was spot-verified manually
rather than via a new automated fixture: `lint:`'s ruff-check stage
still fails on the same ~48 pre-existing I001 findings it does today
(same underlying invocation, no new behavior); `ty` passes clean;
`frob format` genuinely rewrote broken code on scratch input outside
the test suite (import sort, spacing, full ruff-format). Not bound to
a test -- disclosed gap, no fixture-corpus mechanism existed in scope
to build one cheaply here.

Gates: `frob check --ticket T-2244 --only ruff --skip-ruff-format
--only ty` and `frob check --ticket T-2244 --only gates` both clean of
any finding in this ticket's own files; the SCOPE001 noise seen
mid-ticket (T-2251's own unlanded commits sharing this worktree) is
gone now that T-2251 is landed ahead of this ticket, per the series
order.

This ticket's own commits ride the same series worktree as T-2251
(the sibling that must land first, per this ticket's original
blocked_by=T-2252 -- superseded once T-2251 built the missing `frob
format` primitive T-2252 identified as the real gap). Landed together
via --allow-cross-ticket on T-2251's land, in declared series order.

### Changed
```
 tickets/T-2244/ticket.md | 8 ++++++--
 1 file changed, 6 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_makefile_coverage.py::TestFormatLintTypecheckRecipesDelegateToFrob::test_format_calls_frob_format_select_imports_only` (pytest node id, verified passing when recorded)
- `tests/unit/test_makefile_coverage.py::TestFormatLintTypecheckRecipesDelegateToFrob::test_lint_fix_calls_frob_format_full_rule_set` (pytest node id, verified passing when recorded)
- `tests/unit/test_makefile_coverage.py::TestFormatLintTypecheckRecipesDelegateToFrob::test_lint_calls_frob_check_ruff_no_format_check_plus_ty` (pytest node id, verified passing when recorded)
- `tests/unit/test_makefile_coverage.py::TestFormatLintTypecheckRecipesDelegateToFrob::test_typecheck_calls_frob_check_only_ty` (pytest node id, verified passing when recorded)
- `tests/unit/test_makefile_coverage.py::TestTestRecipesUseFrobTestPathSelection::test_test_calls_frob_test_all` (pytest node id, verified passing when recorded)
- `tests/unit/test_makefile_coverage.py::TestTestRecipesUseFrobTestPathSelection::test_test_unit_scopes_frob_test_to_tests_unit` (pytest node id, verified passing when recorded)
- `tests/unit/test_makefile_coverage.py::TestTestRecipesUseFrobTestPathSelection::test_test_integration_scopes_frob_test_to_tests_integration` (pytest node id, verified passing when recorded)
- `tests/unit/test_makefile_coverage.py::TestTestRecipesUseFrobTestPathSelection::test_test_system_scopes_frob_test_to_tests_system` (pytest node id, verified passing when recorded)
- `tests/unit/test_makefile_coverage.py::TestTestRecipesUseFrobTestPathSelection::test_test_fast_keeps_raw_pytest_testmon_disclosed_gap` (pytest node id, verified passing when recorded)
- `tests/unit/test_makefile_coverage.py::TestRepointedTargetsStillFailNonzeroOnRealViolations::test_frob_format_exits_nonzero_on_an_unfixable_syntax_error` (pytest node id, verified passing when recorded)
- `tests/unit/test_makefile_coverage.py::TestRepointedTargetsStillFailNonzeroOnRealViolations::test_frob_check_ty_exits_nonzero_on_a_real_type_error` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 11 passed (from 11 evidence id(s))
- gates: 35 error(s), 739 warning(s), 703 waived
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC002@src/frob/gates/_milestone.py, DOC006@tickets/T-2691/ticket.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, E501@/home/logan/projects/frob/.claude/worktrees/pyfmt-series/src/frob/gates/_fix_engine.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/gates/_milestone.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2244, RENDER001@src/frob/release/_cli.py, SEC004@tests/test_tickets_organization.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md

### Acceptance amendments
- [0] replace: "GIVEN the Makefile WHEN read THEN format:/lint:/lint-fix:/typecheck: recipes call 'uv run frob fmt' / 'uv run frob quality check' instead of raw ruff/ty invocations" -> "GIVEN the Makefile WHEN read THEN format:/lint:/lint-fix:/typecheck: recipes call 'uv run frob format'/'uv run frob check --only ...' instead of raw ruff/ty invocations" (reason: premise correction: frob fmt is directive-comment canonicalization not ruff, and frob quality check bundles ruff-check+ruff-format inseparably with no write mode -- T-2251 built frob format and frob check's existing --only/--skip-ruff-format stage selection is the real replacement, per this ticket's own 2026-08-16/2026-08-18 Failure log entries; logan, 2026-08-19)
- [1] replace: "GIVEN the Makefile WHEN read THEN test:/test-fast:/test-unit:/test-integration:/test-system: recipes call 'uv run frob quality test' (with the matching path/flags) instead of raw pytest invocations" -> "GIVEN the Makefile WHEN read THEN test:/test-unit:/test-integration:/test-system: recipes call 'uv run frob test' with T-2319's directory-scoped path selection; test-fast: stays on raw pytest --testmon (disclosed no-frob-equivalent gap)" (reason: premise correction: frob quality test has no directory-scoped selection at ticket-file time -- T-2319 landed frob test PATH's subset semantics since, which is the real replacement; logan, 2026-08-19)
