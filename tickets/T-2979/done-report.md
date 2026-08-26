## Done report

Changed:
  src/frob/logging/config.toml (stdout handler default INFO not DEBUG)
  src/frob/logging/logger.py (_resolve_stdout_level_override, -v/FROB_VERBOSE/FROB_LOG_LEVEL)
  src/frob/__main__.py (global -v/--verbose flag, _apply_verbose_env_override)
  src/frob/app/doctor_runner.py::run (plain path now wraps run_diagnosis in quiet_query_stdout)
  docs/modules/logging.md (Default verbosity section)
  tests/unit/test_logging_module.py (TestResolveStdoutLevelOverride, config fixture)
  tests/unit/test_main_entry.py (TestVerboseFlag)
  tests/unit/test_doctor_runner_t1276.py (TestDoctorRunnerPlainPathQuieted)

Evidence: 13 pytest node ids bound via `frob ticket evidence` (see ticket.md);
all 65 tests in the three touched test files pass:
`timeout 100 uv run pytest tests/unit/test_logging_module.py
tests/unit/test_main_entry.py tests/unit/test_doctor_runner_t1276.py
-p no:cacheprovider -q` -> SUITE-RESULT: exitstatus=0 collected=65 failed=0.

Manual verification (real CLI, not just unit tests):
- `frob -v gitlog` restores `process: spawning [...]` chatter that default
  `frob gitlog` hides.
- `frob status --json` on the SAME code (main root, unmodified) had gitio/
  process DEBUG lines leaking directly onto STDOUT ahead of the JSON
  payload, corrupting it -- this worktree's `frob status --json` stdout is
  clean, valid JSON (base level INFO hides the DEBUG lines that were
  corrupting it). This is a beneficial side effect, not a behavior change
  to the JSON schema itself.
- `frob ticket show T-2979 --json`: byte-identical between main root and
  this worktree (diff empty) -- proves the well-behaved --json path (one
  already wrapped in quiet_stdout_logs/quiet_query_stdout) is unaffected.
- `frob status --json` run twice still emits the `REDUNDANT_RERUN`
  WARNING-level footgun tip on stderr at default verbosity -- must-still-
  show fixture, confirmed live (not just asserted in a test).
- `frob --help` lists `-v, --verbose`.

Filed: none (in-scope doctor_runner.py gap added to scope, not filed
separately, since it was directly in the ticket's own cited example).

Gates: `frob check --budget 400 --ticket T-2979` -- zero NEW findings
attributable to this change (the only hit inside my touched files,
`src/frob/logging/quiet.py:146` SEC110, was already `frob:waive`d before
this ticket and is unmodified code). All other FAILs in that run are
repo-wide/pre-existing (scope-note: `--ticket` only scopes SCOPE/PREWORK/
diff-driven COV/FMT/AFFECT, everything else repo-wide) -- none reference
any file this ticket touched. `frob fmt` applied (directive-comment
wrapping only, on my own two test files); reverted the 5 unrelated Rust
files it also reformatted, out of scope.

### Changed
```
 docs/modules/logging.md                | 24 ++++++++++
 src/frob/__main__.py                   | 40 ++++++++++++++++
 src/frob/app/doctor_runner.py          | 18 ++++++-
 src/frob/logging/config.toml           |  6 ++-
 src/frob/logging/logger.py             | 57 ++++++++++++++++++++++
 tests/unit/test_doctor_runner_t1276.py | 84 ++++++++++++++++++++++++++++++++
 tests/unit/test_logging_module.py      | 88 +++++++++++++++++++++++++++++++++-
 tests/unit/test_main_entry.py          | 38 +++++++++++++++
 tickets/T-2979/ticket.md               | 62 +++++++++++++++++++++++-
 9 files changed, 413 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/unit/test_logging_module.py::TestResolveStdoutLevelOverride::test_no_flag_or_env_var_is_none` (pytest node id, verified passing when recorded)
- `tests/unit/test_logging_module.py::TestResolveStdoutLevelOverride::test_dash_v_in_argv_is_debug` (pytest node id, verified passing when recorded)
- `tests/unit/test_logging_module.py::TestResolveStdoutLevelOverride::test_dash_dash_verbose_in_argv_is_debug` (pytest node id, verified passing when recorded)
- `tests/unit/test_logging_module.py::TestResolveStdoutLevelOverride::test_frob_verbose_env_var_is_debug` (pytest node id, verified passing when recorded)
- `tests/unit/test_logging_module.py::TestResolveStdoutLevelOverride::test_frob_log_level_env_var_is_parsed` (pytest node id, verified passing when recorded)
- `tests/unit/test_logging_module.py::TestResolveStdoutLevelOverride::test_unrecognized_frob_log_level_is_none_not_a_crash` (pytest node id, verified passing when recorded)
- `tests/unit/test_logging_module.py::test_config_toml_stdout_default_level_is_info_not_debug` (pytest node id, verified passing when recorded)
- `tests/unit/test_main_entry.py::TestVerboseFlag::test_dash_v_sets_debug_env_var` (pytest node id, verified passing when recorded)
- `tests/unit/test_main_entry.py::TestVerboseFlag::test_dash_dash_verbose_sets_debug_env_var` (pytest node id, verified passing when recorded)
- `tests/unit/test_main_entry.py::TestVerboseFlag::test_no_verbose_flag_leaves_env_var_untouched` (pytest node id, verified passing when recorded)
- `tests/unit/test_main_entry.py::TestVerboseFlag::test_existing_explicit_frob_log_level_is_not_clobbered` (pytest node id, verified passing when recorded)
- `tests/unit/test_doctor_runner_t1276.py::TestDoctorRunnerPlainPathQuieted::test_plain_path_raises_stdout_handlers_to_warning_by_default` (pytest node id, verified passing when recorded)
- `tests/unit/test_doctor_runner_t1276.py::TestDoctorRunnerPlainPathQuieted::test_plain_path_leaves_stdout_handlers_alone_under_frob_verbose` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 13 passed (from 13 evidence id(s))
- gates: 42 error(s), 555 warning(s), 854 waived
- error-findings: AFFECT001@src/frob/__main__.py, AFFECT001@src/frob/app/doctor_runner.py, ARCH001@src/frob/app/doctor_runner.py, ARCH103@src/frob/tickets/_new_renumber.py, COV001@scripts/branch_stranded_work_analysis.py, COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/guides/coordinator-scripts.md, DOC006@docs/modules/gates.md, DOC006@tickets/T-2886/ticket.md, DOC006@tickets/T-2962/ticket.md, DOC007@tests/unit/test_doctor_runner_t1276.py, DOC007@tests/unit/test_logging_module.py, DOC007@tests/unit/test_main_entry.py, DOC008@docs/commands/check.md, DRIFT002@tests/unit/test_doctor_runner_t1276.py, DRIFT002@tests/unit/test_logging_module.py, DRIFT002@tests/unit/test_main_entry.py, LARGE001@src/frob/__main__.py, LARGE001@src/frob/stats/_agentic.py, PII012@src/frob/app/doctor_runner.py, PII012@src/frob/serve/_socketd.py, PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-2979, SEC110@src/frob/__main__.py, SEC110@src/frob/logging/logger.py, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md
