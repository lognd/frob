## Done report

Measured on Windows CI run 34371162715 (win4.log): gate:COV had 56 errors, dominated by COV003, traced to tests/unit/test_stackdump.py using pytest.skip(..., allow_module_level=True) guarded by a sys.platform check -- pytest --collect-only never emits those node ids on Windows, so bound frob:tests/evidence for them fails _evidence_valid_for_ticket and COV003 reports "does not resolve to a collected test", indistinguishable from a genuinely missing test.

Searched tickets/*/ticket.md for an existing platform-conditional-evidence ticket first (none found).

Implemented the same shape as the existing missing_natives distinct-cause field (T-0333): pytest --collect-only -rs's skip summary can only ever report a SKIPPED line for a module-level allow_module_level=True skip (per-test skipif decorators are evaluated at setup time, never during collection), so parsing it is a precise signal. Added CollectedTests.platform_skipped ((file, reason) pairs), populated it in collect_python_tests via a module-global mirroring missing_natives' pattern, and had COV003 attribute a matching evidence id as a WARN naming the excluding platform and reason instead of its usual ERROR. Additive, not a blanket exemption -- verified with a second test that unrelated missing evidence in a different file still errors when platform_skipped is non-empty.

Known limitation (documented in code, not a silent gap): on a pytest-collection CACHE HIT, platform_skipped reads back empty since the cache only stores node ids, not skip reasons -- out of this ticket's scope to fix (would need its own cache entry).

### Changed
```
 src/frob/gates/__init__.py         | 65 +++++++++++++++++++++++++---
 src/frob/testing/_collect.py       | 88 +++++++++++++++++++++++++++++++++++++-
 src/frob/testing/_models.py        | 10 ++++-
 tests/gates_suite/test_coverage.py | 65 ++++++++++++++++++++++++++++
 tickets/T-4382/ticket.md           |  3 ++
 5 files changed, 222 insertions(+), 9 deletions(-)
```

### Evidence
- `tests/gates_suite/test_coverage.py::TestCoverageGate::test_cov003_attributes_platform_skipped_evidence_as_warn_not_error` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_coverage.py::TestCoverageGate::test_cov003_unrelated_missing_evidence_still_errors_when_platform_skipped_present` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
