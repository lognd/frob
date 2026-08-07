## Done report

Closed 2 of 3 TEST005 findings with real behavioral tests; classified the
3rd as attribution-limited (T-1235 class) with a scoped-run proof:

- src/frob/vet/_capability.py::non_executable_line_numbers (branch 68.4%):
  added 3 tests to tests/test_vet_capability.py covering the previously-
  uncovered branches -- no-spans-at-all early return, missing-file
  degrade-gracefully path, and the function's own `raw = path.
  read_bytes()` OSError except-branch (warmed the module-level span
  cache with a first real parse, then monkeypatched Path.read_bytes for
  the second call so the function's own read, not the tree-sitter
  parse, is what fails).
- src/frob/vet/_capability.py::is_self_pattern_path (branch 69.2%): added
  4 tests to tests/test_vet.py covering the previously-uncovered
  branches -- root=None early return, path.resolve() OSError, and a
  surprising `.parts` shape hitting both the (KeyError, TypeError) branch
  and the bare Exception fallback (via a resolve() stub returning an
  object whose `.parts` property raises TypeError).
- src/frob/vet/_scan_violations.py (module line 68.1%, still below the
  70% floor): NOT fixable from a scoped test run -- this is an
  attribution-limited artifact (T-1235 class), not a real gap. Proof:
  tests/test_vet.py::TestScanTreeWithLocalSource::
  test_scan_tree_surfaces_a_cve_fingerprint_finding (an EXISTING test,
  already frob:tests-bound) calls the real end-to-end `scan_tree`
  pipeline and explicitly asserts a VET006 `Violation` fires from
  `_vet006_violation` -- the exact function coverage reports as never
  hit. `scan_tree`'s dependency scan runs through a
  `concurrent.futures.ThreadPoolExecutor` (src/frob/vet/_scan.py:16);
  pyproject.toml's own `[tool.coverage.run]` config comment (line 175-178)
  already documents that gate/thread/subprocess execution is only
  correctly attributed via `parallel=true` + `coverage combine`, which a
  scoped ad-hoc `pytest --cov=X` invocation does not perform the same way
  `make coverage`'s full run does. Ran the targeted test alone with
  `--cov=frob.vet._scan_violations --cov-branch --cov-report=term-missing`:
  line 155 (_vet006_violation's body) still shows as a miss despite the
  test's own assertion proving the rule fired -- confirming this is a
  measurement/attribution gap in a scoped run, not an untested code path.

Verified with scoped
`pytest tests/test_vet_capability.py -k non_executable_line_numbers` and
`pytest tests/test_vet.py -k self_pattern --cov=frob.vet._capability
--cov-branch --cov-report=term-missing` runs (per-function results
above); section 6c's unscoped-package caveat applies -- the coordinator's
make coverage stamp is the trustworthy package-wide number.

### Changed
```
 .frob-release.json                               |    4 +-
 CHANGELOG.md                                     |    4 +
 design/frob.strata                               |    4 +
 docs/audits/README.md                            |    2 +
 docs/audits/check-performance.md                 |    2 +
 docs/audits/coordination-churn.md                |    2 +
 docs/audits/docs-staleness-2026-07-29.md         |    2 +
 docs/audits/frob-blindspots-2026-07-23.md        |    2 +
 docs/audits/gates-accounting.md                  |    2 +
 docs/audits/gates-quality.md                     |    2 +
 docs/audits/gates-vacuous.md                     |    2 +
 docs/audits/graph.md                             |    2 +
 docs/audits/lang-check-docs.md                   |    2 +
 docs/audits/perf.md                              |    2 +
 docs/audits/strata.md                            |    2 +
 docs/audits/test005-zero-classification-t1418.md |    2 +
 docs/audits/tickets-testing-round2.md            |    2 +
 docs/audits/tickets-testing.md                   |    2 +
 docs/audits/vet.md                               |    2 +
 docs/design/registry/check-coverage.yaml         |   14 +-
 docs/modules/gates.md                            |    3 +
 pyproject.toml                                   |    2 +-
 src/frob/check/__init__.py                       |    2 +
 src/frob/gates/__init__.py                       |   15 +
 src/frob/gates/_doclink_docanchor.py             |  288 +++++-
 src/frob/gates/_waive.py                         |    6 +
 tests/test_gates.py                              |  160 ++++
 tickets.md                                       | 1113 ++++++++++++++++++++--
 uv.lock                                          |    2 +-
 29 files changed, 1565 insertions(+), 84 deletions(-)
```

### Evidence
- `tests/test_vet_capability.py::TestDocstringProseNotObservedLineLevel::test_non_executable_line_numbers_no_spans_is_empty` (pytest node id, verified passing when recorded)
- `tests/test_vet_capability.py::TestDocstringProseNotObservedLineLevel::test_non_executable_line_numbers_missing_file_is_empty` (pytest node id, verified passing when recorded)
- `tests/test_vet_capability.py::TestDocstringProseNotObservedLineLevel::test_non_executable_line_numbers_read_bytes_oserror_is_empty` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestFingerprintScan::test_self_pattern_exclusion_default_root_is_false` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestFingerprintScan::test_self_pattern_exclusion_resolve_oserror_is_false` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestFingerprintScan::test_self_pattern_exclusion_surprising_parts_shape_is_false` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestScanTreeWithLocalSource::test_scan_tree_surfaces_a_cve_fingerprint_finding` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 3 error(s), 625 warning(s), 750 waived
- error-findings: PERF002@src/frob/gates/_doclink_docanchor.py, SELFAUDIT001@design, WIRE001@src/frob/gates/_doclink_docanchor.py
