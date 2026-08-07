## Done report

`_parse_line_el` computed the branch percentage as
`int(cond_cov.split("(")[-1].split("%")[0].strip())`. For the real
Cobertura value `"50% (1/2)"`, `split("(")[-1]` yields `"1/2)"`, and
`split("%")[0]` leaves that untouched, so `int()` raised EVERY time and
the except branch silently fell back to `100 if hits > 0 else 0`.

The percentage was therefore never read. `symbol_branch` was not branch
coverage at all -- it was "was this line hit".

Measured on this repo's own coverage.xml, before and after:
- before: 2 distinct values, 100 (1963 lines) and 0 (8063)
- after:  3 distinct values, 100 (639), 50 (1324), 0 (8063)

So 1324 partially-covered branch lines were reading as FULLY covered.
Every TEST005 threshold, every floor in frob-coverage.lock.json, and the
whole TEST005 backlog are computed from this number.

Fix is `cond_cov.split("%")[0]`. The except-branch fallback is correct for
genuinely malformed input and stays; T-1371 added tests pinning it.

Expect corrected numbers to move DOWN for partially-covered code and to
surface TEST005 findings that were previously invisible. The ratchet
floors in frob-coverage.lock.json need re-baselining against honest data
rather than being clamped as a regression -- that re-baseline is NOT done
here and must happen on a green `make coverage` run.

### Changed
(no changed files detected)

### Evidence
- `tests/test_gates.py::TestConditionCoverageIsActuallyParsed::test_partial_condition_coverage_is_read_verbatim` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestConditionCoverageIsActuallyParsed::test_three_way_partial_is_not_snapped_to_an_extreme` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestConditionCoverageIsActuallyParsed::test_zero_and_full_condition_coverage_round_trip` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 9 error(s), 2066 warning(s), 695 waived
- error-findings: ARCH103@src/frob/app/_daemon_proxy.py, COV001@src/frob/app/_daemon_proxy.py, DOC007@src/frob/app/_daemon_proxy.py, DRIFT002@src/frob/app/_daemon_proxy.py, E501@/home/logan/projects/frob/src/frob/tickets/_land.py:1231, F401@/home/logan/projects/frob/tests/unit/test_scope_lease_deadlock.py:25, F841@/home/logan/projects/frob/tests/unit/test_scope_lease_deadlock.py:215, PRE001@tickets/T-1376, SELFAUDIT001@design
