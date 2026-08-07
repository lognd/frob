## Done report

Changed:
- `src/frob/check/_python.py::_severity_counts_summary` (new) -- shared
  helper: `"N error(s), M warning(s)"` over a list of `Diagnostic`s
  (zero-count categories omitted), falling back to a caller-supplied
  `no_issues` phrase when there is nothing to report. Never emits a bare,
  unlabelled count.
- `src/frob/check/_python.py::_run_cycle` -- summary now built with
  `_severity_counts_summary(diags, no_issues="no cycles")` instead of the
  old `f"{n} cycle(s) found"`, so a warn-class-only cycle report (the
  reported "pass frob-cycle 1 cycle found" case) reads as "1 warning", not
  an alarming bare count.
- `src/frob/check/_python.py::_run_gates` -- summary now always splits
  into `"{n_err} error(s), {n_warn} warning(s), {n_waived} waived"`
  instead of the old `f"{len(violations)} violation(s), {len(waived)}
  waived"`. `violations` (the gate-report field name) is never surfaced as
  the word "violation(s)" in the rendered summary; a passing gate with
  only warn-class findings now reads "N errors" as "0 errors, M
  warnings, K waived", not a scary undifferentiated count next to a green
  "pass" icon.

Scope note: the ticket's declared scope initially listed
`src/frob/gates/**` for "gates summary rendering" but the actual
per-tool-summary code that produced 'violation(s)'/'cycle found' lives in
`src/frob/check/_python.py` (the check-stage runner, not the gates rule
engine in `src/frob/gates/__init__.py`, which was correctly left
untouched per the dispatch note about T-0191's concurrent clones-gate
lane). Extended the ticket's `scope` to add
`src/frob/check/_python.py` explicitly (SCOPE001 fired on it) before
proceeding; re-ran `frob ticket sweep T-0228` afterward. No other file
outside the (now-extended) declared scope was touched.
`src/frob/gates/__init__.py` was not touched.

Behavior:
- `frob check`'s "Tool summary" line for the `gates` stage on a passing
  run with only warn-class findings now reads e.g. `pass  gates  0
  errors, 3 warnings, 27 waived  [...]` instead of `pass  gates  30
  violation(s), 27 waived  [...]`.
- `frob-cycle`'s summary on a run with only warn/info-class cycles now
  reads `pass  frob-cycle  1 warning` (or `no cycles` when there are none
  at error/warning severity) instead of `pass  frob-cycle  1 cycle
  found`.
- The overall header line (`CheckResult.as_text`, T-0202's PASS/WARN/FAIL
  split) was already correct and untouched -- this ticket only fixed the
  per-tool "Tool summary" lines that fed off `ToolResult.summary`.

Evidence:
- `tests/unit/test_check.py::TestSummarySeverityHonesty::test_warn_only_gate_summary_splits_errors_and_warnings`
  -- new. Monkeypatches `frob.gates.run_gates` to return a single
  WARN-severity `Violation`; asserts `_run_gates`'s `ToolResult.exit_code
  == 0`, `"violation" not in summary`, and the summary contains `"1
  warning"`, `"0 error"`, `"0 waived"`.
- `tests/unit/test_check.py::TestSummarySeverityHonesty::test_cycle_summary_splits_by_severity`
  -- new. Calls `_severity_counts_summary` directly on a single
  warning-severity cycle diagnostic; asserts `"violation" not in summary`,
  `"found" not in summary`, and `summary == "1 warning"`.
- Both collected via `uv run pytest tests/unit/test_check.py::TestSummarySeverityHonesty --collect-only -q -o addopts=""`
  (2 tests collected) and passed via `uv run pytest tests/unit/test_check.py -q`
  (21 passed, includes the 2 new tests plus all 19 pre-existing
  `test_check.py` tests, none regressed).
- Live confirmation on this repo's own tree: `uv run frob check --delta
  --ticket T-0228` went from `FAIL  gates  5/5 new  2 errors, 3 warnings,
  27 waived` (pre-fix baseline had unrelated pre-existing SCOPE001/PRE001
  noise from the scope-widening step, now resolved) to a clean `pass
  gates  3/3 new  0 errors, 3 warnings, 27 waived` and `pass
  frob-cycle  no cycles` after the fix -- observed directly in this
  session's terminal output, not estimated.

Filed: none.

Gates: `frob check --delta --ticket T-0228` clean (0 errors on the
`gates` stage; `ruff-check`/`ruff-format`/`ty`/`frob-cycle` all pass).
`uv run ruff check` and bare `ruff check` both clean on
`src/frob/check/_python.py` and `tests/unit/test_check.py`. `uv run ruff
format --check` clean on both files.
