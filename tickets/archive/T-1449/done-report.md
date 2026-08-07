## Done report

Investigated both options the ticket named. The xdist_group pinning
T-1448 already applied (both TestRealGateGreen and TestCoverageTotality
tagged xdist_group(name="selfconform-full-repo-scan")) already resolved
the actual worker-crash mechanism by serializing the two heavy tests onto
one worker -- that part needed no further change.

For peak-memory reduction: found and fixed a genuine redundant-walk
defect in src/frob/strata/_selfconform.py. _sorted_capability_files(root)
(a full, [graph].exclude-filtered tree walk + sort) was called TWICE per
check_self_conformance() invocation -- once inside _capability_binding
(to build the owner map) and again, completely independently, inside
_coverage_totality_violations (to iterate all files again for the SYS103
join). check_self_conformance now walks once and threads the resulting
list through _bind_conformance_inputs -> _capability_binding and
_collect_sys_violations -> _coverage_totality_violations, halving the
walk cost of every check_self_conformance call (both production frob sys
audit runs and both full-repo-scan tests). Both functions keep a
capability_files=None fallback (fresh walk) so no other caller/test
needs updating.

Did not touch scan_file_capabilities's own per-file tree-sitter parse
cost (the larger driver of the measured ~400MB peak RSS): that scan
already runs exactly once per file per check_self_conformance call
(T-0830/H5's existing single-scan-per-file property, confirmed by
reading _observed_raw_kinds_by_file's docstring) and SYS103's own scan
covers a DISJOINT (FOREIGN, i.e. unbound) file set from the owned-file
scan the other rules share, so there is no redundant parse to remove
there without changing what SYS103 actually checks. Reducing that
scan's own footprint further (streaming instead of eagerly listing, or
narrowing what SYS103's unrestricted-since-T-1091 scan covers) is a
larger, riskier change the ticket itself flagged as "worth investigating
separately" -- left for a follow-up rather than forced into this pass.

Verification: full tests/unit/strata/test_selfconform.py (72 tests) green
under -n4. Measured
TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant
standalone: 428532 KB (~419MB) maximum RSS, 28.14s wall -- consistent
with the ticket's own ~400MB/~20s baseline (this machine's numbers run
somewhat higher than the ticket's baseline machine); the walk dedup
removes one full-tree walk per call but that walk was not the RSS driver,
so no large peak-RSS drop is claimed -- the tests still pass and the
duplicate work is genuinely gone. frob check --only test --only archgate
--only sys --ticket T-1449: 0 errors (after frob ack on
_coverage_totality_violations's changed signature/body). frob check
--only pii_structural --only prework --ticket T-1449: 0 errors after a
sweep refresh.

frob:waive BUG002 reason="this ticket is a peak-memory/worker-crash investigation, not a logic defect a test can fail-then-pass across a checkout diff -- the designated test passes at both the parent commit and the fix (correctness was never wrong), and the crash mechanism itself (two ~400MB scans landing on separate xdist workers under -n auto) is a resource-contention condition the pre-existing xdist_group pinning (T-1448) already serializes; this ticket's own fix (deduping the capability-file walk) is a genuine perf improvement with no correctness change to reproduce as a repro-at-parent failure"

### Changed
```
 docs/strata/selfconform.md           |  13 ++
 frob.lock                            |   4 +-
 src/frob/strata/_selfconform.py      |  83 +++++++++--
 src/frob/tickets/_leases.py          |  49 +++++++
 tests/test_doctor.py                 |  24 ++--
 tests/test_prework_parity.py         |  16 +++
 tests/test_ticket_land.py            |  32 +++++
 tests/test_ticket_leases.py          |  46 ++++++
 tests/unit/perf/test_serial_pools.py |  23 ++-
 tickets.md                           | 271 ++++++++++++++++++++++++++++++++++-
 10 files changed, 528 insertions(+), 33 deletions(-)
```

### Evidence
- `tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_repo_unrestricted_scan_is_clean` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_foreign_file_with_capability_fires_sys103` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
