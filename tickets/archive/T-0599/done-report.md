## Done report

## Done report

Live frob-exports state at start of work (post-merge, drifted from the
2026-07-22 measurement in the ticket body): src/frob 12 missing, src/frob/app
14 missing (13 module `run` + telemetry, plus 2 more found during
verification: app.config.load_arch_config/stale_install_warning, total 16),
src/frob/check 4 missing. Every symbol was traced to at least one
cross-module consumer (grep across src/ and tests/) before being exported --
none were dead/internal-only, so nothing was demoted to private.

Changed:
- src/frob/__init__.py -- export frob.doctor's verify_derived_state,
  run_diagnosis, NativeExtensionStatus, DerivedArtifactStatus, DoctorReport;
  frob.excludes' walk_pruned, iter_files; frob.gitio's spawn_recorder,
  git_common_dir, reset_common_dir_cache, common_dir_and_branch,
  SpawnRecorder. frob.__main__.main stays deliberately unexported (existing
  documented decision, unchanged).
- src/frob/app/__init__.py -- alias+export the 6 runner modules missing from
  the `_runner_run` pattern (clean_runner, debt_runner, doctor_runner,
  fleet_runner, pool_runner, registry_runner -- same dynamic-dispatch shape
  as the other 25 already exported), all 9 frob.app.telemetry symbols
  (is_disabled, iso_now, redact_command, append_event, tree_hash,
  estimate_tokens, record_cli_event, record_ticket_event, timed_call), and
  frob.app.config's load_arch_config/stale_install_warning.
- src/frob/check/__init__.py -- export frob.check._memo's
  reset_run_memo, run_memo_stats, memoize_per_run (run_memo_scope was
  already imported but not in __all__; now included too).

Disposition: every symbol above was EXPORTED (no demotions, no waivers).
None were sole-use-within-own-module -- each had at least one confirmed
cross-module import site.

Evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
- tests/unit/test_config.py::test_stale_install_warning_flags_version_mismatch
- tests/unit/test_config.py::test_missing_toml_defaults
- tests/test_excludes.py::test_walk_pruned_does_not_descend_venv_or_git
- tests/test_excludes.py::test_iter_files_git_fast_path_matches_ls_files
- tests/test_gitio.py::TestSpawnRecorder::test_tallies_spawns_made_inside_the_block
- tests/test_gitio.py::TestGitCommonDir::test_resolves_absolute_common_dir
- tests/unit/test_memo.py::test_reset_run_memo_activates_an_unbounded_scope
- tests/unit/test_memo.py::test_run_memo_scope_deactivates_on_exit
- tests/unit/test_check.py::TestRunCheck::test_all_stages_skipped_returns_empty_result_for_root
- Import smoke: `python -c "import frob, frob.app, frob.check; [getattr(frob, n) for n in frob.__all__]; [getattr(frob.app, n) for n in frob.app.__all__]; [getattr(frob.check, n) for n in frob.check.__all__]"` -- resolved cleanly (24/52/11 symbols).
- `frob check --ticket T-0599 --only static`: frob-exports(src/frob),
  frob-exports(src/frob/app), frob-exports(src/frob/check) report ZERO
  findings (absent from the tool-summary list entirely -- every other
  package's pre-existing findings are untouched/out of scope).
- `frob check --ticket T-0599 --only lint`: 0 errors, 0 warnings (ruff-check,
  ruff-format, ty all pass) after `ruff format`/`ruff check --fix`.
- `frob check --ticket T-0599 --only prework`: 0 errors after re-running
  `frob ticket sweep T-0599`.
- `frob test --base main` (full suite, ran in background per playbook 6b):
  pre-existing failures only (native-extension-availability doctor tests,
  strata self-model, render_lint gitless-root warning path, a
  `_STAGE_GROUPS` coverage gap for the new `protocol_summary` gate landed by
  T-0813) -- none touch src/frob/__init__.py, src/frob/app/__init__.py, or
  src/frob/check/__init__.py; none are new regressions from this change.

Filed: T-0824 (bug) "protocol_summary gate missing from
_STAGE_GROUPS coverage" -- scope src/frob/check/__init__.py's
_STAGE_GROUPS membership, found while running `frob test --base main`
during verification, out of T-0599's exports-only scope.

Gates: `frob check --ticket T-0599 --only static/--only lint/--only prework`
all clean (0 errors/0 warnings on the touched packages). `--only gates-fast`
and `--only gates-native`/`--only gates-security` not separately reported
here beyond the prework/static/lint slices above since no gate logic was
touched by this ticket (pure __init__.py re-export additions); nothing new
observed in those groups tied to the three touched files.

Deviations from plan: none. All 3 packages resolved to 0 exports findings
via export (not demotion or waiver), matching the ticket's "explicit
decision, exported/demoted/waived" requirement -- the decision made for
every symbol was "export" since every one had a genuine cross-module
consumer.

### Changed
(no changed files detected)

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)
- `tests/unit/test_config.py::test_stale_install_warning_flags_version_mismatch` (pytest node id, verified passing when recorded)
- `tests/unit/test_config.py::test_missing_toml_defaults` (pytest node id, verified passing when recorded)
- `tests/test_excludes.py::test_walk_pruned_does_not_descend_venv_or_git` (pytest node id, verified passing when recorded)
- `tests/test_excludes.py::test_iter_files_git_fast_path_matches_ls_files` (pytest node id, verified passing when recorded)
- `tests/test_gitio.py::TestSpawnRecorder::test_tallies_spawns_made_inside_the_block` (pytest node id, verified passing when recorded)
- `tests/test_gitio.py::TestGitCommonDir::test_resolves_absolute_common_dir` (pytest node id, verified passing when recorded)
- `tests/unit/test_memo.py::test_reset_run_memo_activates_an_unbounded_scope` (pytest node id, verified passing when recorded)
- `tests/unit/test_memo.py::test_run_memo_scope_deactivates_on_exit` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRunCheck::test_all_stages_skipped_returns_empty_result_for_root` (pytest node id, verified passing when recorded)
