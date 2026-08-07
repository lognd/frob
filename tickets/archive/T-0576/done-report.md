## Done report

frob:debt generalized to the API surface: `frob:deprecated <since>
sunset="YYYY-MM-DD" ticket="T-####" [reason="..."]` on a public symbol
mirrors DEBT001/DEBT002/DEBT003's shape (dsl.py's `_parse_attrs`,
`_KNOWN_GATE_RULES`, `deprecated_gate` alongside `debt_gate`), with one
deliberate difference from debt: a deprecation is visible even while
still valid. DEPR001 (malformed directive/bad sunset), DEPR002 (bound to
a non-open ticket -- the "ticket closes without removal" case), DEPR003
(WARN, still inside its window -- unlike debt, which is silent until
something is wrong), DEPR004 (ERROR, past sunset). `release_gate` refuses
to stamp while any deprecation is past sunset (REL001), but -- unlike
debt, which blocks a release for ANY open debt -- a still-in-window
deprecation does not block a release.

Not done in this pass, filed as follow-ups rather than silently folded
in: no CLI subcommand analogous to `frob debt` (T-0576 scoped only
graph/gates/docs/tests) -- filed T-0638 (ex-draft, id lost at land); no "gained new
callers" trigger (the ticket body itself does not require it --
`frob.graph.callgraph`'s caller/reference graphs only resolve PRIVATE
callees by design, so reusing them for a public deprecated symbol's
callers is not a drop-in fit and needs its own design) -- filed
T-0639 (ex-draft, id lost at land). Both convert to real T-#### ids at the next `frob
ticket land`/renumber pass.

### Changed
```
 docs/guides/extending/comment-dsl-directives.md |  36 +-
 docs/modules/gates.md                           |  48 +++
 src/frob/gates/__init__.py                      | 287 ++++++++++++++
 src/frob/gates/_models.py                       |  16 +
 src/frob/graph/_models.py                       |   7 +
 src/frob/graph/dsl.py                           |  30 ++
 tests/test_gates.py                             | 173 +++++++++
 tests/unit/graph/test_dsl.py                    |  64 +++
 tickets.md                                      | 494 +++++++++++++++++++++++-
 9 files changed, 1142 insertions(+), 13 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestDeprecatedGate::test_depr001_malformed_directive_is_reported` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDeprecatedGate::test_depr001_malformed_sunset_is_reported` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDeprecatedGate::test_depr002_closed_ticket_is_reported` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDeprecatedGate::test_depr003_in_window_warns` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDeprecatedGate::test_depr004_past_sunset_errors` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDeprecatedGate::test_clean_deprecated_produces_no_violations` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDeprecatedGate::test_lists_every_deprecated_entry` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDeprecatedGate::test_release_gate_fails_while_deprecated_is_past_sunset` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDeprecatedGate::test_release_gate_silent_while_deprecated_in_window` (pytest node id, verified passing when recorded)
- `tests/unit/graph/test_dsl.py::TestDeprecatedDirective::test_well_formed_directive_parses_to_deprecated_edge` (pytest node id, verified passing when recorded)
- `tests/unit/graph/test_dsl.py::TestDeprecatedDirective::test_missing_sunset_is_malformed` (pytest node id, verified passing when recorded)
- `tests/unit/graph/test_dsl.py::TestDeprecatedDirective::test_missing_ticket_is_malformed` (pytest node id, verified passing when recorded)
- `tests/unit/graph/test_dsl.py::TestDeprecatedDirective::test_non_date_sunset_is_malformed` (pytest node id, verified passing when recorded)
