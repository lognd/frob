## Done report

WHICH HALF WAS WRONG: the verdict logic in `CheckResult.as_text`, not the
detail text. `ok = r.passed and r.error_count == 0` keyed FAIL off the raw
subprocess exit code (`ToolResult.passed`), independent of whether any
diagnostic was actually found. `ty`/`ruff-format`'s parsers
(`summarize_severity(empty="no issues")`, `_ruff_format_result`'s
`f"{n} files..."` with `n == 0`) both report a genuinely clean-looking
summary whenever `diagnostics` is empty -- regardless of exit_code. So a
nonzero exit with zero diagnostics rendered a FAIL row whose own detail
text said nothing was wrong: a manufactured failure, not a stale or
misassembled string. A run that DOES carry a diagnostic
(tool_unavailable_result, tool_disabled_result, ruff-check's own
malformed-JSON parse error) already attaches a real error diagnostic and
was never affected by this bug.

UNMEASURED WAS BEING COLLAPSED INTO FAIL: confirmed. This is the same
"could not determine a real answer" ambiguity T-1664's UNRESOLVED/UNRES
vocabulary (T-2891) already names for gate: families, reached here via a
bare nonzero exit code instead of an explicit info-severity diagnostic.
Routed it into the existing UNRES rendering/Unmeasured gates roster (new
_is_silent_nonzero_exit predicate) rather than inventing a third icon or
silently downgrading to pass.

Filed T-4321 for an out-of-scope discovery: T-4309's given scope
(the whole check/__init__.py file) carries pre-existing SCOPE002 closure
debt across 130+ unrelated symbols/files, plus a possible WARN-severity-
rendered-as-error miscategorization in the same gate; both predate this
diff and are unrelated to it (reproducible against untouched symbols).

### Changed
```
 src/frob/check/__init__.py           | 178 +++++++++++++++++++++++++++++------
 tests/unit/test_check_measurement.py | 100 ++++++++++++++++++--
 tickets/T-4309/ticket.md             |  26 +++++
 tickets/T-4321/ticket.md   |  29 ++++++
 4 files changed, 296 insertions(+), 37 deletions(-)
```

### Evidence
- `tests/unit/test_check_measurement.py::TestSilentNonzeroExit::test_listed_in_unmeasured_results` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_measurement.py::TestSilentNonzeroExit::test_as_text_renders_unres_not_fail` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_measurement.py::TestSilentNonzeroExit::test_as_text_lists_reason_with_exit_code_and_summary` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_measurement.py::TestSilentNonzeroExit::test_a_real_failure_with_diagnostics_still_renders_fail` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_measurement.py::TestUnmeasuredResults::test_empty_when_every_result_measured` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_measurement.py::TestUnmeasuredResults::test_lists_every_not_measured_result` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 3 error(s), 4680 warning(s), 955 waived
- error-findings: ARCH103@src/frob/graph/cache.py, SCOPE002@tickets.md, TODO002@src/frob/gates/_land_format.py
