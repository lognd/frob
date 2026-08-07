## Done report

Classified all 306 TEST005 symbol-level findings that reported exactly
0.0% branch coverage in the 2026-08-02 make coverage run
(source_sha=7454ba65), per the brief's exact number (1443 unwaived
TEST005 total, 306 at exactly 0.0%, matched exactly by extracting
gate:TEST diagnostics from `frob check --only test --json`).

Method: resolved each symbol's frob:tests-bound covering test(s)
(multi-line-continuation-aware parse), deduplicated to 91 unique test
files, ran them ALL TOGETHER in one serial (-n0, no xdist) pytest
invocation with --cov=src/frob --cov-branch and the same
COVERAGE_PROCESS_START subprocess-tracing config make coverage uses, then
re-ran frob's OWN TEST005 scorer (not a hand-rolled reimplementation)
against that batch's coverage.xml to classify each symbol against the
same 75% threshold.

Result: 306 of 306 classified. 283 attribution artifacts (standalone
>=75%, frob's own passing bar), 23 attribution artifacts with real but
still-partial standalone coverage (named test exists and is exercised,
but genuine additional coverage remains below threshold even standalone),
0 genuine gaps. Every row has a named, checkable covering test. Three
spot-checked by hand against the actual test source to confirm real
assertions, not incidental import-time execution.

Structural finding (contradicts the brief's subprocess/daemon/CLI-entry
concentration prediction): only 16 of 306 (15 mixed + 1 subprocess-only)
are covered by any subprocess/system/integration test; 289 of 306 (94%)
are covered EXCLUSIVELY by ordinary in-process unit tests. A live
reproduction during this investigation found a more precise candidate
root cause: running the SAME 91-file covering-test batch under -n4
(xdist) plus a separate manual `coverage combine` call silently zeroed
src/frob/__main__.py's coverage entirely, while the -n0/single-invocation
form (used for this classification) correctly showed 76%. make coverage
itself uses xdist workers plus a separate `coverage combine` step
(Makefile:213-252) -- structurally the same shape as the failing
reproduction. Filed T-1426 to investigate this directly against
the real make coverage worker count, since it is out of this
classification-only ticket's scope to chase further.

Deliverable: docs/audits/test005-zero-classification-t1418.md (method,
results, per-package summary, prediction check) plus
docs/audits/test005-zero-classification-t1418.csv (all 306 rows:
file|symbol|classification|standalone_branch_pct|covering_tests).

Cut: did not classify the other 1137 unwaived TEST005 findings (170 at
10-19%, 107 at 20-49%, 119 at 50-74%, 413 module-line findings) --
out of this ticket's declared 306-symbol scope. Did not write any tests,
per the ticket's explicit instruction.

### Changed
```
 design/frob.strata                                 |   1 +
 docs/audits/README.md                              |   1 +
 docs/audits/test005-zero-classification-t1418.csv  | 307 ++++++++++++
 docs/audits/test005-zero-classification-t1418.md   | 186 ++++++++
 .../unit/test_docs_test005_classification_t1418.py |  50 ++
 tickets.md                                         | 514 ++++++++++++++++++++-
 6 files changed, 1056 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/unit/test_docs_test005_classification_t1418.py::TestClassificationCsv::test_has_exactly_306_rows` (pytest node id, verified passing when recorded)
- `tests/unit/test_docs_test005_classification_t1418.py::TestClassificationCsv::test_every_row_has_a_named_covering_test` (pytest node id, verified passing when recorded)
- `tests/unit/test_docs_test005_classification_t1418.py::TestClassificationCsv::test_classification_totals_match_the_audit_doc` (pytest node id, verified passing when recorded)
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 1 error(s), 325 warning(s), 691 waived
- error-findings: TICK006@tickets.md
