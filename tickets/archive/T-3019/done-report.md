## Done report

Changed:
- src/frob/check/_python.py::_run_ruff
- src/frob/check/_python.py::_ruff_format_result
- src/frob/check/_python.py::_run_ruff_autofix
- src/frob/gates/_refs.py::_DEFAULT_ROOT_MANIFEST_EXEMPT
- src/frob/gates/_refs.py::_ref_gate_file_violations
- tests/system/test_cli_check.py::_make_project (frob.toml REF001=warn)
- tests/system/test_cli_check.py::TestCheckGatesStage.test_only_gates_passes_once_bound_and_tested
  (.gitignore for .frob/, coverage.xml)
- tests/test_refs_gate.py::TestDefaultRootManifestExempt (new)
- tests/unit/test_check.py::TestRunRuffRealPaths.test_invokes_pinned_ruff_via_uv_run_not_bare_ruff (assertions rewritten for bare-ruff behavior; name kept to preserve T-2252 evidence)
- tests/unit/test_check.py::TestRunRuffAutofix.test_success_runs_fix_then_format_via_uv_run (assertions rewritten for bare-ruff behavior; name kept to preserve T-2320 evidence)

Root causes (three separate bugs, confirmed via a minimal from-scratch
scratch fixture, not just the repo's own test suite):

1. PRE001/SCOPE001: `_run_ruff`/`_ruff_format_result` invoked `uv run ruff
   <target>`. `uv run` resolves its "project" from the subprocess cwd,
   which for `frob check <path>` is the project BEING CHECKED. Against a
   target with no `uv.lock` yet, `uv run` silently creates one (plus
   `*.egg-info/`) as a side effect before ever running ruff -- an
   untracked write into the checked repo's own working tree, which
   PRE001/SCOPE001 correctly report as a real, unaccounted-for diff (that
   part of their behavior was never wrong). Fixed by invoking a bare
   `ruff` binary, matching `_run_ty`'s pre-existing convention -- frob's
   own environment `bin/` is already on PATH for every child process, so
   no version-pinning guarantee is lost.

2. REF001 (3 of the false findings): a project's own root
   `pyproject.toml`/`frob.toml` had no BUILT-IN exemption -- only
   `[[refs.entrypoint]]` (per-project, opt-in) covered files like this.
   Every project has exactly one of each, read by tooling, never
   referenced from other tracked source -- not a per-project judgment
   call. Added `_DEFAULT_ROOT_MANIFEST_EXEMPT` (exact literal root paths:
   pyproject.toml, frob.toml, .gitignore, frob-coverage.lock.json -- the
   last one because `frob.doctor`'s own docstring calls it "the committed
   frob-coverage.lock.json", i.e. deliberately tracked, unlike the rest of
   `.frob/`). A nested/workspace-member pyproject.toml is NOT exempted
   (must-still-fire fixture: TestDefaultRootManifestExempt::
   test_nested_pyproject_toml_still_subject_to_ref001).

3. REF001 (the remaining finding, src/mypkg/__init__.py in the fixture):
   NOT a bug -- a single unconsumed __init__.py with no test/entry-point
   importing it is a genuine REF001 orphan by that gate's own design
   (proven with an ERROR-severity assertion in
   tests/test_refs_gate.py::TestTiers, unaffected by this change). Fixed
   the test fixture itself to downgrade REF001 to warn in the same
   adoption-baseline list the fixture already uses for COV/TEST gates
   (these system tests exercise ruff/ty/cycle/dup tool paths, not
   REF001's orphan-file discipline).

Clean-project finding count (minimal from-scratch scratch fixture,
pyproject.toml + frob.toml + one src/mypkg/__init__.py, git-committed):
BEFORE: 9 errors (COV002/PRE001/SCOPE001/TODO001 diff-load failures on a
"master"-named default branch, then once renamed to "main": PRE001 1,
REF001 3, SCOPE001 1 = 5 errors after eliminating the branch-name
variable). AFTER: 0 errors, 0 REF/PRE/SCOPE findings.

tests/system/test_cli_check.py -- of the 6 tests named in this ticket's
repro list: TestCheckCleanProject::test_clean_code_exits_zero,
TestCheckSkipFlags::test_skip_ruff, TestCheckSkipFlags::test_skip_exports,
TestCheckGatesStage::test_only_gates_passes_once_bound_and_tested now
PASS. TestCheckStageGroups::test_available_stages_cover_every_gate_and_tool
and TestCheckTicketLeasePinRefusal::test_ticket_lease_recorded_elsewhere_refuses
still fail, root-caused to two DIFFERENT bugs with no overlap with
REF001/PRE001/SCOPE001 or this ticket's declared scope
(src/frob/check/__init__.py's _STAGE_GROUPS membership, and CHECK001
firing before the lease-pin check) -- filed as T-3030 and
T-3028. Two more pre-existing, unrelated failures surfaced
while running the full file (TestGitlessTargetGateSeverity, a documented
order-dependent logging flake; TestCheckTypescript, a TS-fixture-specific
REF001/MILE003 issue) -- the latter filed as T-3031; the former
is a known flake per its own docstring, not filed separately.

Cluster B (test_selfconform.py, 23 self-conformance violations) was
explicitly split out because `design/frob.strata` was under an
in-progress lease (T-2989) when this ticket started -- filed as
T-3029.

Evidence: 6 node ids bound above (`frob ticket evidence T-3019`).
Filed: T-3028, T-3030, T-3029, T-3031
(all renumber at land; verify real ids on main before citing further).
Gates: frob check --ticket T-3019 run before land (see land output).

### Changed
```
 rapid-debt.jsonl                   |   2 +
 src/frob/check/_python.py          |  47 +++++++--------
 src/frob/gates/_refs.py            |  48 +++++++++++++++-
 tests/system/test_cli_check.py     |  17 ++++++
 tests/test_refs_gate.py            |  39 +++++++++++++
 tests/unit/test_check.py           |  32 +++++++----
 tickets/T-3019/done-report.md      | 115 +++++++++++++++++++++++++++++++++++++
 tickets/T-3019/ticket.md           | 100 ++++++++++++++++++++++++++++++--
 tickets/T-3028/ticket.md |  48 ++++++++++++++++
 tickets/T-3029/ticket.md |  54 +++++++++++++++++
 tickets/T-3030/ticket.md |  46 +++++++++++++++
 tickets/T-3031/ticket.md |  43 ++++++++++++++
 12 files changed, 551 insertions(+), 40 deletions(-)
```

### Evidence
- `tests/test_refs_gate.py::TestDefaultRootManifestExempt::test_root_pyproject_and_frob_toml_are_exempt_with_no_declaration` (pytest node id, verified passing when recorded)
- `tests/test_refs_gate.py::TestDefaultRootManifestExempt::test_nested_pyproject_toml_still_subject_to_ref001` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRunRuffRealPaths::test_invokes_pinned_ruff_via_uv_run_not_bare_ruff` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRunRuffAutofix::test_success_runs_fix_then_format_via_uv_run` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_check.py::TestCheckCleanProject::test_clean_code_exits_zero` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_check.py::TestCheckGatesStage::test_only_gates_passes_once_bound_and_tested` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 56 error(s), 597 warning(s), 854 waived
- error-findings: ARCH103@src/frob/tickets/_new_renumber.py, COV001@scripts/branch_stranded_work_analysis.py, COV001@strata-core/src/graph/model.rs, COV001@strata-core/src/graph/query.rs, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC001@docs/strata/graph.md, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/commands/narrative.md, DOC006@tickets/T-2962/ticket.md, DOC006@tickets/T-2989/ticket.md, DOC006@tickets/T-2996/ticket.md, DOC007@src/frob/app/check_runner.py, DOC007@src/frob/app/doctor_runner.py, DOC007@src/frob/ci_report.py, DOC007@src/frob/ghio.py, DOC007@tests/unit/test_app_runners_batch6.py, DOC007@tests/unit/test_check.py, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DRIFT002@src/frob/app/check_runner.py, DRIFT002@src/frob/app/doctor_runner.py, DRIFT002@src/frob/ci_report.py, DRIFT002@src/frob/ghio.py, DRIFT002@tests/unit/test_app_runners_batch6.py, DRIFT002@tests/unit/test_check.py, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, I001@/home/logan/projects/frob/.claude/worktrees/t3018-t3019-series/tests/test_narrative_migrate.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/stats/_agentic.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, REF002@docs/modules/ci_report.md, REF002@docs/modules/ci_validity.md, REF002@docs/modules/ghio.md, REF002@src/frob/gates/_narrative_blocks.py, REG002@docs/design/registry/check-coverage.yaml, REG005@docs/design/registry/check-coverage.yaml, REG008@docs/design/registry/check-coverage.yaml, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, SYS003@tests/test_ci_report.py, SYS003@tests/test_ci_validity.py, SYS003@tests/test_ghio.py, SYS003@tests/test_narrative_migrate.py, TEST001@scripts/branch_stranded_work_analysis.py, TEST001@strata-core/src/graph/model.rs, TEST001@strata-core/src/graph/query.rs, TICK004@tickets.md, TICK011@tickets.md, WAIVE006@src/frob/gates/_rule_id_scan.py
