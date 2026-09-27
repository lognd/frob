## Done report

Assets/Tests/... NUnit fixtures were reoriented backwards because looks_like_test_path decided test-shapedness from path text alone; deciding from the language collector's own grammar (NUnit attributes, pytest-discoverable names) instead fixes the misclassification at its root and keeps the path rule only as the documented fallback.

### Changed
```
 docs/modules/graph.md        |  37 ++++++++--
 src/frob/graph/__init__.py   |  33 +++++++--
 src/frob/graph/dsl.py        | 160 ++++++++++++++++++++++++++++++++++++-------
 tests/unit/graph/test_dsl.py | 101 +++++++++++++++++++++++++++
 tickets/T-6570/ticket.md     |   5 +-
 5 files changed, 300 insertions(+), 36 deletions(-)
```

### Evidence
- `tests/unit/graph/test_dsl.py::TestUnityNUnitTestSideIsCollectorNotPathDecided::test_hullbreach_shipbody_test_side_directive_binds_cleanly` (pytest node id, verified passing when recorded)
- `tests/unit/graph/test_dsl.py::TestUnityNUnitTestSideIsCollectorNotPathDecided::test_hullbreach_shipbody_test_side_declaration_is_not_flagged_redundant` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
