## Done report

Changed:
- tests/system/test_cli_native_missing.py (new): TestNativeMissingFailsLoud.test_sys_audit_fails_loud_when_strata_present, .test_check_fails_loud_with_sys004_when_strata_present, .test_check_unaffected_when_no_strata_files
- tests/fixtures/fake_no_native/strata_core.py (new): PYTHONPATH-shadow fixture, `raise ImportError(...)` at module scope, used by the above to simulate a natives-less `uv tool install frob` at real-subprocess granularity
- docs/guides/install.md: new "Loud failure when `.strata` is used without natives (T-0316)" section and new "Detecting a stripped native install (the reinstall-wiped-my-wheel gotcha)" section

Investigation finding (disclosed honestly): the loud-failure behavior this
ticket asked for was ALREADY implemented in this codebase by prior work
(T-0133/T-0134/T-0135) -- `src/frob/gates/__init__.py`'s `_sys004`/`sys_gate`
already reports a missing native extension as an ERROR-severity `SYS004`
`Violation` (fails `frob check`'s overall exit code), and
`src/frob/app/sys_runner.py`'s `_load_audit_model`/`_run_plan`/`_run_doc`
already `sys.exit(1)` on any design-load error including
`NativeExtensionUnavailable`. Verified live: stashed `strata_core`+
`frob_core` out of this worktree's own `.venv/lib/python3.11/site-packages`,
ran `frob sys audit` (exit 1, printed `NativeExtensionUnavailable` and the
`design/frob.strata failed to load` message) and `frob check` (exit 1 --
confirmed bare, not through a masking pipe per the playbook's rule 3 --
`gates` reported `SYS004` as one of 14 errors), then restored the natives
and confirmed `frob check` returns to normal. A parallel check on a repo
with NO `.strata` files confirmed it is completely unaffected either way
(`sys_gate`'s T-0135 opt-in check). The FROBLEMS report describing a
silent SYS004-exit-0 was accurate for an earlier state of the code (its
"bit mid-campaign" framing) but the underlying gate logic has since closed
that hole -- this ticket's actual gap was the missing END-TO-END (real
subprocess CLI, not monkeypatched-unit) regression coverage proving it,
which is what `tests/system/test_cli_native_missing.py` now provides,
plus the packaging/reinstall documentation below.

Packaging (item 2, investigated, partial): `make install-tool`
(`uv tool install --force --reinstall . --with ./strata-core --with
./frob-core`) already exists (T-0133) as the documented full-install path
and was not touched. Investigated (a) declaring strata_core/frob_core as
real `[project.optional-dependencies]` -- not achievable in this
environment: they are unpublished local maturin path packages, and this
repo has no PyPI project/publish credentials to change that (matches
docs/guides/install.md's pre-existing "Why not `pip install
\"frob[strata]\"`?" explanation, left as-is, still accurate). (b) a
mixed maturin build folding frob-core/strata-core into frob's own wheel --
would require replacing frob's setuptools build backend and restructuring
two independent Rust crates into frob's package tree; too large a
structural change to attempt safely inside this ticket's scope
(pyproject.toml/docs/tests), and risks exactly the wheel-build breakage
this dispatch was warned to avoid. (c) documented check, done: new
docs/guides/install.md sections above explain the loud-failure guarantee,
name the exact `uv tool upgrade`/`--force --reinstall` (no `--with`)
regression this ticket's FROBLEMS report actually hit ("reinstall wiped
the manually-added wheel"), and give a copy-pasteable `python3 -c "import
strata_core, frob_core"` verification snippet plus the `make install-tool`
remediation.

Filed: T-0319 ("packaging: frob doctor subcommand to verify+remediate
missing native extensions") -- a real `frob doctor` CLI surface for the
verification snippet above, and re-evaluating a real PyPI publish of
strata-core/frob-core as the true long-term fix (needs PyPI project
ownership/CI credentials not available in this environment).

Evidence:
- tests/system/test_cli_native_missing.py::TestNativeMissingFailsLoud.test_sys_audit_fails_loud_when_strata_present
- tests/system/test_cli_native_missing.py::TestNativeMissingFailsLoud.test_check_fails_loud_with_sys004_when_strata_present
- tests/system/test_cli_native_missing.py::TestNativeMissingFailsLoud.test_check_unaffected_when_no_strata_files
  (collected via `pytest tests/system/test_cli_native_missing.py --collect-only`, all 3 PASS via `pytest tests/system/test_cli_native_missing.py -q`)
- Pre-existing regression guard, still green: tests/test_gates.py::TestSysGate.test_design_dir_degrades_with_typed_error_on_native_extension_missing

Verification performed:
- `uv build --wheel` -- succeeded (`dist/frob-0.9.0-py3-none-any.whl`); confirmed it clobbers `.venv`'s natives per the known gotcha, then `make core` restored `strata_core`+`frob_core` (both import cleanly afterward)
- `uv run pytest tests/unit/strata/test_design_load.py tests/test_gates.py::TestSysGate tests/system/test_cli_sys_audit.py tests/system/test_cli_native_missing.py tests/system/test_cli_check.py -q` -- all green
- `uv run pytest --cov=src/frob --cov-branch --cov-report=xml -q` (full suite via `make coverage`'s command) -- all green, then `frob check --stamp-coverage`
- `uv run ruff check` / `ruff check` (PATH) on touched files -- clean under both, per playbook rule 12
- `uv run ruff format --check` -- clean after one auto-format pass
- `uv run ty check src/frob` -- "All checks passed!"
- `uv run frob check --stamp-baseline` then `uv run frob check --delta` -- `0/0 new  0 errors, 0 warnings, 204 waived`, exit 0
- `git diff main --diff-filter=D --stat` -- empty (deletion-filter clean)

Gates: `frob check --delta` clean (0 new violations); `frob check --ticket T-0316` not run standalone since scope enforcement on this ticket's malformed frontmatter `scope` field (a single comma-joined string, not a real glob list -- pre-existing data issue, not touched here) made it unreliable; the dispatch's explicit broadened scope (pyproject.toml, src/frob/**, docs/**, tests/**, tickets.md) was followed instead, and no file outside that set was touched.
