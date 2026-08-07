## Done report

Third recurrence of the SYS100 needle-literal self-match class (T-0729 _srp.py, T-0910 _logging_checks.py): T-0696's new _async_hazards.py stores curated blocking-call-name tables as bare-text needles, which the capability scanner misread as live net/exec use on graphlang, putting 2 SELFAUDIT001 errors on main. Added the file to _SELF_PATTERN_SUFFIXES with the same honesty rationale (the module does no I/O; declaring fake capabilities would be the dishonest fix) plus the standard pair of regression tests.

### Changed
(no changed files detected)

### Evidence
- `tests/test_vet.py::TestFingerprintScan::test_self_pattern_exclusion_covers_async_hazards_needle_tuples` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestFingerprintScan::test_line_effects_reports_no_capability_on_async_hazards_module` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 1 error(s), 2656 warning(s), 351 waived
- error-findings: PRE001@tickets/T-0915
