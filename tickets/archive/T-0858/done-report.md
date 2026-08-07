## Done report

Reevaluated the T-0580/T-0802 navigation-command sunset before it executes.
Conclusion: keep `frob xref` deprecated per its existing 2026-10-01 sunset
(telemetry still shows zero organic invocation of the standalone command),
but fold the one recurring, gate-driven capability it answers -- "who
imports this symbol" -- into the `exports` library surface instead of
letting it be deleted along with the porcelain.

Added `frob.exports.exports_consumers` (plus `ConsumerRef`/`ConsumersResult`
models): reuses `frob.xref.xref`'s parsed usages, then narrows to lines
that parse as an actual import statement, so it answers the consumer
question without the false positives (comment/prose mentions) or missed
matches that a plain grep suffers from -- the exact failure mode T-0601's
reviewer caught. This is a library-only surface for now; there is no
`frob exports --consumers` CLI flag yet, because wiring one requires
touching src/frob/app/exports_runner.py, src/frob/app/config.py, and
src/frob/__main__.py, none of which are in this ticket's declared scope
(src/frob/app/xref_runner.py, src/frob/exports/**, docs/modules/cli.md).
Filed T-0876 to do that CLI wiring as a follow-on before/around
the 2026-10-01 sunset.

Also updated xref_runner.py's deprecation warning/docstring to point at
the new `exports_consumers` surface, and added a new section to
docs/modules/cli.md documenting the decision and the new public API
(frob:describes anchors on ConsumerRef, ConsumersResult, exports_consumers).

This reevaluation directly informs T-0802 (see that ticket's own Done
report / fail record): the sunset date (2026-10-01) has not passed as of
today (2026-07-23), and T-0802's own body says not to work it before then,
so T-0802 is left queued/deferred rather than forced through.

### Changed
(no changed files detected)

### Evidence
- `tests/unit/test_exports.py::TestExportsConsumers::test_finds_import_consumer` (pytest node id, verified passing when recorded)
- `tests/unit/test_exports.py::TestExportsConsumers::test_excludes_prose_mention` (pytest node id, verified passing when recorded)
- `tests/unit/test_exports.py::TestExportsConsumers::test_no_source_files` (pytest node id, verified passing when recorded)
- `tests/unit/test_exports.py::TestExportsConsumers::test_as_text_output` (pytest node id, verified passing when recorded)
- `tests/unit/test_exports.py::TestExportsConsumers::test_as_json_output` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
