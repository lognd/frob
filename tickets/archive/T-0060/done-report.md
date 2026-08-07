## Done report

Changed:
- src/frob/strata/_elaborate.py::elaborate (new)
- src/frob/strata/_elaborate.py::_elaborate_node (new, private)
- src/frob/strata/_elaborate.py::_elaborate_flow (new, private)
- src/frob/strata/_elaborate.py::_elaborate_boundary (new, private)
- src/frob/strata/_elaborate.py::_elaborate_claim_body (new, private)
- src/frob/strata/_elaborate.py::_elaborate_claim (new, private)
- src/frob/strata/_elaborate.py::_validate_no_duplicates (new, private)
- src/frob/strata/_elaborate.py::_validate_references (new, private)
- src/frob/strata/__init__.py (export `elaborate`)
- docs/strata/surface.md (new "## Elaborator" section)

Evidence:
- tests/unit/strata/test_elaborate.py::TestElaborateFullMapping::test_maps_every_construct_field_for_field
- tests/unit/strata/test_elaborate.py::TestElaborateValidation::test_duplicate_node_id_fails_closed
- tests/unit/strata/test_elaborate.py::TestElaborateValidation::test_boundary_referencing_unknown_flow_fails_closed
- tests/unit/strata/test_elaborate.py::TestElaborateAbstract::test_abstract_marker_preserved_in_attrs
- tests/unit/strata/test_elaborate.py::TestElaborateEndToEnd::test_parse_elaborate_evaluate_matches_expected_verdicts

Filed: none

Gates: `frob check --ticket T-0060` exit 0. `uv run pytest tests/unit/strata -q` green (69 tests). `uv run ruff format`/`ruff check` clean. `uv run ty check` clean on src/frob/strata and tests/unit/strata.

### Reviewer round 2 (rejected, both findings fixed)

The reviewer rejected the first pass on two MAJOR findings:

1. The structured `evidence:` YAML list above had only 3 node ids while
   this Done report's prose listed 5. Reconciled by adding the two
   missing node ids (`TestElaborateValidation::test_boundary_referencing_unknown_flow_fails_closed`
   and `TestElaborateAbstract::test_abstract_marker_preserved_in_attrs`)
   to the structured `evidence:` list, verified against
   `uv run pytest --collect-only tests/unit/strata/test_elaborate.py`.
2. `TestElaborateEndToEnd` only drove PROVED verdicts through the
   parse -> elaborate -> evaluate_claims pipeline. Added a third node
   (`rogue`, trust `foreign`) and flow (`f4: rogue -> audit`, no
   boundary) plus claim `c3 noflow foreign -> audit` to the same test, and
   asserted `Verdict.REFUTED` with the exact witness counterexample
   `("rogue", "f4", "audit")`, alongside the existing PROVED claims.

Re-ran the full verification loop after both fixes: `uv run pytest
tests/unit/strata -q` green (70 tests); `ruff format`/`ruff check` +
`ty check` clean on `src/frob/strata` and `tests/unit/strata`; `frob
graph build`; `frob ticket sweep T-0060` (last); `frob check --ticket
T-0060` exit 0.
