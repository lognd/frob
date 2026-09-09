## Done report

Changed:
- src/frob/gates/_doclink_docanchor.py::doclink_gate (now also runs DOC014)
- src/frob/gates/_doclink_docanchor.py::_doc014_row_section_pairing (new)
- src/frob/gates/_doclink_docanchor.py::_doc014_registry_table_rows (new)
- src/frob/gates/_doclink_docanchor.py::_doc014_doc_headings (new)
- src/frob/gates/_doclink_docanchor.py::_doc014_broken_pairings (new)
- src/frob/gates/_doclink_docanchor.py::_doc014_violation (new)

Determination (required by acceptance): DOC002 has NO hole. Proven by
construction with the real build_graph scan (not a hand-built Edge): a
frob:doc comment pointing at a non-existent anchor fires DOC002
identically from a .py symbol and a .ts symbol
(test_unresolvable_anchor_fires_identically_python_and_typescript),
falsifying the TS-symbol-collection-gap hypothesis. Also confirmed via
`frob check --only docanchor --no-cache`: 0 DOC002 violations in this
repo today -- no burn-down ticket needed, the reported incident's repo
(logand.app-v2) is not this repo and this repo carries no equivalent
dangling pointer.

Added DOC014 (row<->section table pairing, both directions, one
violation per document) for the second, cheaper ask -- opt-in via a
table header literally reading Component/Symbol/Section so it never
guesses at tables that never claimed to be a row-per-section registry
(verified quiet against docs/audits/graph.md's real "Component" table,
which is prose-per-row, not a slug registry, and correctly produces no
violation).

T-4127 interaction: DOC014, like DOC002, requires a real 1:1 row<->
heading pairing per document -- it pushes the SAME "one file, many
per-symbol anchors" doc shape T-4127 found scope-closure-punishing.
Anyone doing T-4127 should know DOC014 now also depends on that shape
existing correctly, not just DOC002.

Evidence:
- tests/gates_suite/test_doc.py::TestDocanchorGate::test_unresolvable_anchor_fires_identically_python_and_typescript
- tests/gates_suite/test_doc.py::TestDoc014RowSectionPairing (5 tests: real-anchor-quiet, row-without-section, section-without-row, one-violation-per-doc, non-registry-table-ignored)

Filed: none (no burn-down needed; repo measured clean)

Gates: `frob check --ticket T-4139` clean (0 errors). check-repro could
not run post-land-shape (T-2025's own documented limitation: no ancestor
commit exists with the test but not the fix, since this is pre-land);
ran the 6 new/changed tests directly instead -- all pass -- plus the
full `frob test --base main` touched-set (15 python tests, exit=0).

### Changed
```
 CHANGELOG.md                         |   3 +
 frob.lock                            |  46 ++++++++++
 src/frob/gates/_doclink_docanchor.py | 168 ++++++++++++++++++++++++++++++++++-
 tests/gates_suite/test_doc.py        | 148 ++++++++++++++++++++++++++++++
 tickets/T-4139/done-report.md        |  68 ++++++++++++++
 tickets/T-4139/ticket.md             |  12 ++-
 6 files changed, 438 insertions(+), 7 deletions(-)
```

### Evidence
- `tests/gates_suite/test_doc.py::TestDocanchorGate::test_unresolvable_anchor_fires_identically_python_and_typescript` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_doc.py::TestDoc014RowSectionPairing::test_real_anchor_still_passes` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_doc.py::TestDoc014RowSectionPairing::test_row_with_no_matching_section_fires` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_doc.py::TestDoc014RowSectionPairing::test_section_with_no_matching_row_fires` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_doc.py::TestDoc014RowSectionPairing::test_reported_once_per_document_not_per_row` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_doc.py::TestDoc014RowSectionPairing::test_table_not_named_component_symbol_or_section_is_ignored` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_doc.py::TestDocanchorGate::test_unresolvable_anchor_fires` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 0 error(s), 4790 warning(s), 958 waived
- error-findings: none (measured, zero errors)
