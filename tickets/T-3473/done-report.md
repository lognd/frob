## Done report

Coordinator widened scope to include src/frob/arch/_normalized.py and src/frob/arch/_python.py so the missing model capability could be added. Minimal model extension: NormalizedModule.module_regex_patterns (bare_name -> pattern_text) records every top-level 'NAME = re.compile(PATTERN)' assignment (_py_top_level_regex_patterns/_py_string_literal_raw_text in _python.py) -- the ONE deliberate exception to the module's no-top-level-statement rule, documented as such. _mayraise.py gained _regex_group_guard_discharges: for int(x)/float(x) whose sole arg matches '<name>.group(<N>)', if func.calls has EXACTLY ONE <pattern>.search()/.match() call whose receiver is a known module_regex_patterns key, that pattern's group N is exactly \d+ (via _regex_capturing_group_texts/_regex_group_is_digit_only), and a branch at or before the call contains '<name> is None' in its condition_text, the ValueError contribution is discharged -- ambiguous receivers, non-digit groups, and a missing None-guard all fail closed (still raise), matching this file's existing textual-guard convention (T-2568's isdigit guard). Removed both frob:waive EXHAUST002 comments (scripts/_require_python.py, scripts/wait_for_land_slot.py) the T-2568 land added. exhaustive_handling: gate:EXHAUST waived count 114 -> 112 (both findings gone entirely, not re-waived); both sites now show only the pre-existing, unrelated EXHAUST003 resolution-coverage warning. Added TestRegexGroupGuardDischarge (must-fire digit-only-after-None-guard; must-stay-quiet: non-digit group, missing guard, ambiguous regex candidates, plus one real end-to-end adapter+resolver test over the exact corpus source shape) and two TestPythonAdapter tests for module_regex_patterns extraction (positive + fail-closed on aliased-import/computed-pattern/non-regex assignment). TestIsdigitGuardDischarge/TestSubscriptProvenance/TestMayRaiseResolver re-run clean, confirming the T-2568 path and subscript provenance are undisturbed. No new tickets filed.

### Changed
```
 tickets/T-3473/ticket.md | 18 +++++++++++++++++-
 1 file changed, 17 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_arch.py::TestRegexGroupGuardDischarge::test_digit_only_group_after_none_guard_discharges_value_error` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestRegexGroupGuardDischarge::test_non_digit_group_still_raises_value_error` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestRegexGroupGuardDischarge::test_missing_none_guard_still_raises_value_error` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestRegexGroupGuardDischarge::test_ambiguous_regex_call_candidates_does_not_discharge` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestRegexGroupGuardDischarge::test_real_require_python_corpus_site_has_no_leaked_value_error` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestPythonAdapter::test_adapt_records_top_level_regex_compile_pattern_text` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestPythonAdapter::test_adapt_ignores_non_regex_top_level_assignments` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestIsdigitGuardDischarge::test_guarded_int_call_discharges_value_error` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: 15 error(s), 4044 warning(s), 867 waived
- error-findings: AFFECT001@src/frob/arch/_normalized.py, COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC007@src/frob/verify/_bisect.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT002@src/frob/verify/_bisect.py, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PRE001@tickets/T-3473, REL001@src/frob/__init__.py, SELFAUDIT001@tests/unit/verify/test_bisect.py, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
