## Done report

Changed:
- src/frob/process/parsers/ruff.py::parse_ruff_json
- src/frob/process/parsers/ruff.py::parse_ruff
- src/frob/process/parsers/ty.py::parse_ty

Evidence:
- tests/unit/test_tool_absent_parser_reconcile.py (12 tests, all passing) --
  covers ruff-check's absent-tool classification (with/without stderr
  evidence, wrong exit code, unrelated stderr, and the still-must-stay-an-
  -error malformed-JSON/present-but-broken case), ty's explicit absent-tool
  classification, and a symmetry test asserting both parsers agree on the
  identical spawn-failure shape.
- tests/unit/test_parser_failure_diagnostics.py (regression: T-4308's
  original malformed-JSON/no-output distinctions unchanged)
- tests/unit/test_check_measurement.py, tests/unit/test_project_tool.py
  (regression: T-4309/T-4354 doctrines unchanged)
- `frob check --ticket T-4358`: 0 errors
- `frob test --base main`: python suite PASS (10 tests recorded)

Filed: T-4359 (bug, scope src/frob/check/_python.py) -- the one
real production call site that needs the new `stderr=` parameter wired
through (`_run_ruff`'s `parse_ruff_json(proc.stdout, exit_code=...)` call)
for this fix to take effect on the actual macOS CI path; ty's equivalent
caller already concatenates stdout+stderr so needed no change. That file
is outside T-4358's declared scope (parsers/ruff.py, parsers/ty.py only).

Gates: frob check --ticket T-4358 clean (0 errors); no waivers needed
beyond the two FMT001 waivers for unwrappable long frob:tests directive
lines (same precedent as src/frob/app/pyfmt_runner.py's existing FMT001
waivers) and the AFFECT001 waivers already established by T-4308's own
precedent on this same function.

### Changed
```
 src/frob/process/parsers/ruff.py                |  59 +++++++++--
 src/frob/process/parsers/ty.py                  |  38 +++++++
 tests/unit/test_tool_absent_parser_reconcile.py | 126 ++++++++++++++++++++++++
 tickets/T-4358/done-report.md                   |  51 ++++++++++
 tickets/T-4358/ticket.md                        |  21 ++++
 tickets/T-4359/ticket.md              |  29 ++++++
 6 files changed, 318 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/unit/test_tool_absent_parser_reconcile.py::TestRuffAbsentToolIsUnmeasured::test_spawn_failure_is_unmeasured_not_error` (pytest node id, verified passing when recorded)
- `tests/unit/test_tool_absent_parser_reconcile.py::TestRuffEmptyOutputWithoutStderrEvidenceStaysAnError::test_no_stderr_argument_is_still_an_error` (pytest node id, verified passing when recorded)
- `tests/unit/test_tool_absent_parser_reconcile.py::TestRuffPresentButBrokenStaysAnError::test_truncated_json_is_still_malformed_even_with_stderr_set` (pytest node id, verified passing when recorded)
- `tests/unit/test_tool_absent_parser_reconcile.py::TestTyAbsentToolIsUnmeasured::test_spawn_failure_text_is_unmeasured` (pytest node id, verified passing when recorded)
- `tests/unit/test_tool_absent_parser_reconcile.py::TestBothParsersAgree::test_ruff_and_ty_both_report_zero_errors_on_absent_tool` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 0 error(s), 4783 warning(s), 965 waived
- error-findings: none (measured, zero errors)
