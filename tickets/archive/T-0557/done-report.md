## Done report

## Done report

Changed:
- src/frob/gates/__init__.py::_test005_symbols

Distinguishes "symbol never executed" (its file DOES appear in
`data.module_line`, i.e. coverage.xml measured it, but the symbol itself
has no `symbol_branch` entry) from "symbol's file excluded from
measurement entirely" (no `module_line` entry at all -- not imported by
the suite, a generated file, or otherwise out of scope). The former is now
treated as 0% branch coverage and flagged; the latter is still skipped
(a measurement gap belongs to TEST006/module_join_fraction, not a per-
symbol floor claim). Before this fix, both cases silently skipped, which
combined with B1 (TEST001 name-match) let completely dead public code
clear coverage gates entirely.

Evidence:
- tests/test_gates.py::TestTestGate::test_test005_unmeasured_symbol_in_measured_file_flags_as_zero
- tests/test_gates.py::TestTestGate::test_test005_symbol_in_unmeasured_file_still_skipped

Filed: none

Gates: uv run frob check --ticket T-0557 clean (0 errors, 136 warnings, 177
waived); uv run pytest tests/test_gates.py -q: full file passed (all tests)

### Changed
```
 src/frob/gates/__init__.py | 64 +++++++++++++++++++++++-------
 tests/test_gates.py        | 97 ++++++++++++++++++++++++++++++++++++++++++++++
 tickets.md                 | 80 ++++++++++++++++++++++++++++++++++++--
 3 files changed, 224 insertions(+), 17 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestTestGate::test_test005_unmeasured_symbol_in_measured_file_flags_as_zero` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTestGate::test_test005_symbol_in_unmeasured_file_still_skipped` (pytest node id, verified passing when recorded)
