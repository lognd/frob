## Done report

Changed:
- strata-core/src/parse/mod.rs::Parser::parse_refine
- strata-core/src/parse/mod.rs::ModuleAst (new `refines` field)
- strata-core/src/parse/mod.rs::Parser::parse_program (refine keyword wiring)
- src/frob/strata/_ast.py::RefineDecl
- src/frob/strata/_ast.py::Module (new `refines` field)
- src/frob/strata/_errors.py::StrataError (new `RefinementViolation` member)
- src/frob/strata/_elaborate.py::_rewire_endpoint
- src/frob/strata/_elaborate.py::_rewrite_claim_for_refine
- src/frob/strata/_elaborate.py::_apply_refine
- src/frob/strata/_elaborate.py::_elaborate_refines
- src/frob/strata/_elaborate.py::elaborate (now flattens refine blocks)
- src/frob/strata/__init__.py (export RefineDecl)
- docs/strata/surface.md ("### v0 semantics" under Refinement, Parser
  section RefineDecl anchor + grammar-subset note, Elaborator section
  refine/RefinementViolation notes)
- tests/unit/strata/test_refine.py (new)

Evidence:
- tests/unit/strata/test_refine.py::TestRefineHappyPath::test_flattens_abstract_node_and_rewires_outer_flow
- tests/unit/strata/test_refine.py::TestRefineHappyPath::test_claim_endpoint_rewritten_and_still_evaluable
- tests/unit/strata/test_refine.py::TestRefineHappyPath::test_noflow_claim_proved_at_abstract_level_stays_proved_after_refinement
- tests/unit/strata/test_refine.py::TestRefineViolations::test_refine_of_non_abstract_node_fails
- tests/unit/strata/test_refine.py::TestRefineViolations::test_refine_of_unknown_target_fails
- tests/unit/strata/test_refine.py::TestRefineViolations::test_inner_flow_touching_outer_id_fails_new_external_surface
- tests/unit/strata/test_refine.py::TestRefineViolations::test_foreign_inner_node_under_trusted_abstract_fails_trust_laundering
- tests/unit/strata/test_refine.py::TestRefineViolations::test_bind_to_not_an_inner_node_fails
- tests/unit/strata/test_refine.py::TestUnrefinedFrontier::test_unrefined_abstract_node_keeps_marker
- strata-core/src/parse/mod.rs::tests::parses_refine_happy_path
- strata-core/src/parse/mod.rs::tests::error_refine_zero_binds
- strata-core/src/parse/mod.rs::tests::error_refine_two_binds
- strata-core/src/parse/mod.rs::tests::error_refine_binds_lhs_mismatch
- strata-core/src/parse/mod.rs::tests::error_refine_before_module

Deviations: budget distribution (faithfulness check 3) is explicitly
DEFERRED to phase 2, as instructed -- not implemented, documented in
docs/strata/surface.md and as a code comment in `_apply_refine`.

Filed: T-0091 (`make core` creates a stray venv under strata-core/,
observed while rebuilding the Rust extension for this ticket -- worked
around with an explicit `VIRTUAL_ENV`, not fixed here since it is outside
this ticket's deliverable list).

Gates: `cargo test --lib` in strata-core: 27 passed (5 new refine tests).
`make core` rebuilt both extensions (workaround: `VIRTUAL_ENV=$(pwd)/.venv
uvx maturin develop --uv --release -m strata-core/Cargo.toml`, see T-0091).
`uv run pytest tests/unit/strata -q`: all green (81 tests, 9 new).
`uv run ruff format --check` / `ruff check` clean on all touched files.
`uv run ty check` clean. `frob graph build` clean (11 describes anchors in
docs/strata/surface.md). `frob ticket sweep T-0062` recorded. `frob check
--ticket T-0062` exit 0 (only pre-existing waived PERF003 findings in
unrelated modules).
