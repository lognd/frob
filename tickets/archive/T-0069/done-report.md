## Done report

Changed: strata-core/src/parse.rs (phase_block/operation/node observability
grammar + 7 cargo tests), src/frob/strata/_ast.py (PhaseBlock family,
OperationDecl, ObserveDecl, NodeDecl fields), src/frob/strata/_errors.py
(FrameViolation, CrossStoreAtomicity, UnknownLogClass),
src/frob/strata/_elaborate.py (phase/operation validation + conditioned-
flow construction), src/frob/strata/__init__.py exports,
docs/strata/boundary.md (## v0 implementation), 19 new pytest cases in
tests/unit/strata/test_boundary_phases.py + test_observe.py.
Evidence: 3 pytest node ids above (of 19 new, all green); 71/71 cargo
tests green; full `tests/unit/strata` suite green (155 tests).
Filed: none.
Gates: `frob check --ticket T-0069` exit 0, gates stage executed
(clones/coverage/decisions/doclink/drift/fuzz/invariant/perf/policy/
prework/release/test all ran); plain `frob check` exit 0, no skip.
ruff format/check and ty clean.
