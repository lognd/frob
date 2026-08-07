## Done report

Re-verification round (T-0622), following the T-0625 land squash that
carried this dead-session batch's code onto main while T-0622/T-0623/
T-0624 stayed in-progress with unverified evidence.

### Acceptance criteria verdicts
- unlogged-error-path: SATISFIED. `check_unlogged_error_path` flags an
  except/catch or `return Err(...)` with no log call in a 3-line
  adjacency window (`src/frob/arch/_logging_checks.py`).
- unlogged-boundary: SATISFIED. `check_unlogged_boundary` flags a public
  function/method with no log call anywhere in its body, and any
  subprocess/network/filesystem call site with no nearby log call.
- print-as-diagnostic: SATISFIED. `check_print_as_diagnostic` flags a
  bare `print(...)` outside a CLI-output module (path containing
  `cli`/`__main__`/`console`).
- docs updated including the strata/arch boundary note: SATISFIED --
  docs/modules/arch.md's "Logging discipline checks" section (anchor
  `logging-discipline-checks`) carries the STRATA BOUNDARY NOTE
  disclosing this is logging-IN-CODE only, no runtime/flow correlation.
- fixture per sub-check: SATISFIED -- TestUnloggedErrorPath (2),
  TestUnloggedBoundary (3), TestPrintAsDiagnostic (2),
  TestRunLoggingChecks (1).

### Scope fix
Added `src/frob/arch/_models.py` to declared scope (the committed diff,
f2fa96f3, extends the shared `ArchCategory` with the three new
categories; the ticket's original scope list omitted it).

### Verification
- `uv run pytest tests/unit/test_arch.py -k "UnloggedErrorPath or
  UnloggedBoundary or PrintAsDiagnostic or RunLoggingChecks"
  -p no:cacheprovider -n0 --timeout=300` -- 8 passed, 212 deselected.
- Evidence re-recorded via `frob ticket evidence T-0622 <id>` for all 8
  node ids (idempotent, CLI-bound).
- `git diff main --diff-filter=D --stat` -- empty (code already on main;
  this pass only touches tickets.md).

### Cuts disclosed
- No wiring into `analyze_project`/the check pipeline -- by design, per
  T-0626's own job (not worked here per this dispatch's explicit
  instruction).

### Changed
(no changed files detected)

### Evidence
- `tests/unit/test_arch.py::TestUnloggedErrorPath::test_catch_with_no_nearby_log_call_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestUnloggedErrorPath::test_catch_with_nearby_log_call_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestUnloggedBoundary::test_public_entry_point_with_no_log_call_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestUnloggedBoundary::test_boundary_call_with_no_nearby_log_call_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestUnloggedBoundary::test_private_function_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestPrintAsDiagnostic::test_print_call_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestPrintAsDiagnostic::test_print_call_in_cli_module_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestRunLoggingChecks::test_combines_all_three_checks` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
