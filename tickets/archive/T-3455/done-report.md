## Done report

The failure (assert 0.5013780752997159 < 0.2) passed on 4/4 local runs (single test and full test-class), confirming it is a wall-clock/scheduling-noise defect on a busier shared CI runner, not a code regression -- this is the second time this exact test's absolute threshold has needed loosening (T-2942 went 0.05 -> 0.2; CI now measured 0.50), so a third numeric bump would just repeat the pattern. Replaced both this test and its sibling test_with_serial_pools_worker_is_majority_attributed's assertions with a relative comparison: both fractions (with install_serial_pools() patched in vs not) are now measured within the SAME test invocation and compared against each other (unpatched < patched * 0.5, patched > unpatched * 2, plus a > 0.5 sanity floor on the patched side) rather than either being pinned to an absolute constant a slow/contended runner can miss regardless of whether the real attribution gap T-0948 exists. Verified stable across 3 repeated local runs of the pair plus the full test_serial_pools.py module (9/9 passing).

### Changed
```
 tests/unit/perf/test_serial_pools.py | 49 +++++++++++++++++++++++++-----------
 tickets/T-3455/ticket.md             |  5 +++-
 2 files changed, 39 insertions(+), 15 deletions(-)
```

### Evidence
- `tests/unit/perf/test_serial_pools.py::TestInstallSerialPools::test_without_serial_pools_worker_is_unattributed` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_serial_pools.py::TestInstallSerialPools::test_with_serial_pools_worker_is_majority_attributed` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 14 error(s), 3985 warning(s), 855 waived
- error-findings: COV001@src/frob/tickets/_scope.py, COV003@tickets/T-3410, DEPR006@frob-deprecated-baseline.lock.json, DOC006@tickets/T-3411/ticket.md, DOC007@tests/unit/test_main_entry.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/tickets/_scope.py, DRIFT002@tests/unit/test_main_entry.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PRE001@tickets/T-3455, REL001@src/frob/__init__.py, SELFAUDIT001@design, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
