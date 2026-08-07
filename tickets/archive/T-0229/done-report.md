## Done report

Changed:
- `src/frob/app/check_runner.py::_detected_types` (new) -- enumerates ALL
  language markers present under root, not just `detect_project_type`'s
  single-winner pick.
- `src/frob/app/check_runner.py::_run_all_detected` (new) -- runs every
  detected language stage and merges their `ToolResult`s into one
  `CheckResult` (errors/warnings sum across the merge, so a failure in ANY
  detected stage fails the overall run).
- `src/frob/app/check_runner.py::_skip_note_result` (new) -- synthetic
  `ToolResult` producing a `SKIPPED: <lang> (pinned to <chosen> via
  check_type)` line, appended to the report whenever `check_type` is
  pinned (CLI `--type` or `frob.toml`'s top-level `check_type`) and other
  language markers are also present.
- `src/frob/app/check_runner.py::_warn_if_polyglot` (rewritten) -- now
  only fires for the deliberate pinned-opt-out case (previously fired for
  every auto-detected polyglot repo, which is the bug: warn-then-PASS).
- `src/frob/app/check_runner.py::run` -- auto-detect (`check_type` unset)
  now calls `_run_all_detected` over every detected language marker
  instead of dispatching a single winner; the pinned path appends
  `_skip_note_result` entries for every other detected language and keeps
  the (now honest) `_warn_if_polyglot` warning.

Behavior:
- Unpinned polyglot repo -> every detected language's stage runs (gates
  included for python); a failure in any of them makes the overall exit
  code nonzero, same as a single-language repo.
- Pinned polyglot repo (`--type <lang>` or `frob.toml` `check_type`) ->
  unchanged single-stage behavior, but the text/JSON report now carries an
  explicit `SKIPPED: <other-lang> (pinned to <lang> via check_type)` tool
  entry per excluded language, and a WARNING log line naming what the pin
  excludes -- so the exclusion can never look like an unqualified clean
  PASS.

Evidence:
- `tests/system/test_cli_check.py::TestCheckPolyglot::test_unpinned_polyglot_runs_python_stage`
  -- polyglot fixture (Cargo.toml + pyproject.toml both present), unpinned
  `frob check --json`; asserts `ruff-check` (a python-only tool) is in the
  tool list, proving the python stage ran even though `Cargo.toml` alone
  would have won `detect_project_type`'s single-winner priority.
- `tests/system/test_cli_check.py::TestCheckPolyglot::test_pinned_check_type_reports_skipped_line`
  -- same fixture, `--type python`; asserts the text report contains
  `SKIPPED` and names the excluded `rust` stage.
- Both collected under `pytest --collect-only -q -o addopts=""
  tests/system/test_cli_check.py` (repo addopts forces `-n auto`, which
  hides node ids from `--collect-only`; ran with `-o addopts=""` to
  confirm the exact ids above are real).
- `pytest tests/system/test_cli_check.py -q` (full file, includes the
  2 new tests): `24 passed`.
- `uv run ruff check src/frob/app/check_runner.py tests/system/test_cli_check.py`
  and the same bare `ruff check ...`: `All checks passed!` (both PATH and
  project-pinned ruff, per playbook section 12).
- `uv run ty check src/frob/app/check_runner.py`: `All checks passed!`.

Filed: none -- no out-of-scope work discovered.

Gates: `frob check --delta --ticket T-0229` clean after `frob ticket sweep
T-0229` re-ran the pre-work sweep post-edit (the first delta run correctly
flagged `PRE001` stale-sweep and `SCOPE001` on two `Cargo.lock` files that
`make core`'s build touched during warm-up -- both `Cargo.lock` files were
reverted with `git checkout --`, out of this ticket's scope). Post-fix
delta: `gates 3/3 new` all pre-existing WARNING-level (TEST006 missing
coverage stamp; PERF004/PERF003 in unrelated files `_land.py`/
`_obfuscation.py`) -- none introduced by this change, none ERROR-level, so
gates report `pass`.
