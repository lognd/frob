## Done report

Changed: strata-core/src/parse.rs (node errors_total/panics_contained_by/
observe grammar), src/frob/strata/_ast.py (ObserveDecl, NodeDecl fields),
src/frob/strata/_errors.py (UnknownLogClass), src/frob/strata/_elaborate.py
(_validate_observability, _elaborate_observe_flows), 7 new pytest cases
in tests/unit/strata/test_observe.py (shared file with T-0069's phase/
operation tests). v0 scope note: node-only (store did not gain these
three properties -- grammar deviation documented in
docs/strata/boundary.md#v0-implementation); ERR/OBS gate wiring into
`frob check` is out of scope (phase 4), only declared-structure checks
implemented.
Evidence: 3 pytest node ids above (of 7 new, all green).
Filed: none.
Gates: `frob check --ticket T-0070` exit 0, gates stage executed; plain
`frob check` exit 0. ruff/ty clean.
