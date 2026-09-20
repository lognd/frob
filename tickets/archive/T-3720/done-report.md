## Done report

Registered frob:external-reader as a directly-owned markdown verb in _MD_HANDLED_VERBS (src/frob/graph/dsl.py) so ROOT001's own prescribed remedy no longer trips DSL001 as unhandled. Evidence: tests/unit/graph/test_dsl_markdown_waive.py::TestUnhandledMarkdownWaiveDirective::test_external_reader_directive_produces_no_unhandled_finding (bound, 21/21 file passed). Filed: none. Gates: frob check --ticket T-3720 clean except the pre-existing out-of-scope DEPR006 on frob-deprecated-baseline.lock.json (known, not this ticket's).

### Changed
```
 src/frob/graph/dsl.py                       | 14 +++++++++++++-
 tests/unit/graph/test_dsl_markdown_waive.py | 16 ++++++++++++++++
 tickets/T-3720/done-report.md               | 19 +++++++++++++++++++
 tickets/T-3720/ticket.md                    |  4 +++-
 4 files changed, 51 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/graph/test_dsl_markdown_waive.py::TestUnhandledMarkdownWaiveDirective::test_external_reader_directive_produces_no_unhandled_finding` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 1 error(s), 4320 warning(s), 919 waived
- error-findings: DEPR006@frob-deprecated-baseline.lock.json
