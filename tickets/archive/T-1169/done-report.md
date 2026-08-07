## Done report

Added the missing `frob:enforces CHK-GATE-NATIVE001` edge on `native_
unavailable_warning` in src/frob/strata/_native_staleness.py -- the
single-source-of-truth detection logic `gates/__init__.py::
_native_unavailable_report` (T-1148) wraps into the actual `NATIVE001`
Violation, mirroring the CHK-GATE-SYS103/104/105/106 precedent in
_selfconform.py of binding the edge to the enforcing detection function
rather than the thin GateReport-construction call site.

docs/design/registry/check-coverage.yaml's `CHK-GATE-NATIVE001` entry
already existed (synced via `frob registry audit --sync-gate-rules` per
the ticket's own filing) -- no change needed there, the edge was the
only missing half (REG008).

Added tests/unit/strata/test_native_staleness.py to scope: `frob ticket
land`'s D-02 preflight correctly refused the initial evidence bind (the
registry-exhaustiveness test has no TESTS edge to `_native_staleness.py`
and its own file is not in scope) -- rebound evidence to
TestUnimportableNatives::test_warning_names_the_native_and_the_fix_
command / test_warning_is_none_when_nothing_broken, the two tests
that already carry `frob:tests src/frob/strata/_native_staleness.py::
native_unavailable_warning` directives and directly exercise the
enforcing function.

### Changed
```
 src/frob/strata/_native_staleness.py |  9 ++++++++
 tickets.md                           | 43 +++++++++++++++++++++++++++++++++++-
 2 files changed, 51 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_registry_exhaustiveness.py::TestCheckCoverageReg008BurnDown::test_no_reg008_findings_for_check_coverage_yaml` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_native_staleness.py::TestUnimportableNatives::test_warning_names_the_native_and_the_fix_command` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_native_staleness.py::TestUnimportableNatives::test_warning_is_none_when_nothing_broken` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 0 error(s), 446 warning(s), 498 waived
- error-findings: none (measured, zero errors)
