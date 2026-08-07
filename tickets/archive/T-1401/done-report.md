## Done report

The lock/report disagreement was the T-1363 downward-ratchet clamp substituting the prior committed value on any drop over 2.0 points, with no carve-out for a genuine zero. Verified against the preserved coverage.xml from source_sha=de76e283: __main__.py, serve/_socketd.py and serve/_leases.py all record line-rate=0 there while the lock claimed 81.2/65.1/40.3. The clamp had therefore been hiding exactly the regression class a ratchet exists to catch. Fixed narrowly by excluding an exact 0.0 from the clamp; every non-zero drop keeps T-1363's protection unchanged, locked by its own regression test. load_coverage now enumerates the modules that failed to join instead of reporting only a bare ratio -- the bare 0.53 is what sent an earlier investigation chasing a join defect that did not exist. The 0.53 itself is a separate denominator artifact (851 counts tests/** that coverage.xml can never contain) and is filed separately, not folded in.

### Changed
```
 src/frob/gates/_coverage.py | 138 +++++++++++++++-----
 tests/test_gates.py         | 147 +++++++++++++++++++++
 tickets.md                  | 306 +++++++++++++++++++++++++++++++++++++++++++-
 3 files changed, 554 insertions(+), 37 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestCoverageLoad::test_write_coverage_lock_records_a_genuine_zero` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCoverageLoad::test_write_coverage_lock_still_clamps_a_nonzero_drop` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCoverageLoad::test_unjoined_modules_are_enumerated_not_silently_omitted` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 2 error(s), 400 warning(s), 700 waived
- error-findings: PII012@tests/test_gates_fix_engine.py, PRE001@tickets/T-1401
