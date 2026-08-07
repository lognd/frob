## Done report

Changed: `strata-core/src/lib.rs::propagated_demand` (+ `compute_demand`
helper), `strata-core/src/parse.rs` (`fanout`/`growth`/`skew zipf` props on
node/store/flow, desugar to `attrs`), `strata_core.pyi`,
`src/frob/strata/_facts.py::FactBase.propagated_demand`/`_flow_fanout`,
`src/frob/strata/_claims.py::_eval_bound` (skew hottest-share + growth
horizon), `_node_skew`/`_zipf_hottest_share`/`_flow_growth`/`_add_months`/
`_months_to_saturation`/`GROWTH_HORIZON_MONTHS`. No `_ast.py`/
`_elaborate.py`/`_infra.py` changes needed: the three new props desugar
straight to `attrs` in the Rust parser, which already passes through
field-for-field (law 1). Docs: kernel.md `### Capacity semantics` +
strata-core bullets; surface.md parser section note.
Evidence: see `evidence:` above (3 of 11 new pytest cases + 8 new/updated
cargo tests in strata-core; COV003 cannot resolve cargo names).
Filed: none.
Gates: `frob check --ticket T-0066` and plain `frob check` both exit 0;
cargo test --lib (53 passed), pytest tests/unit/strata (all green), ruff
format/check clean, ty clean. Chose the "honest v0" cycle rule (any cycle
fed by a declared-rate source and reaching target is +inf) over computing
per-cycle fanout products, documented in kernel.md as a deliberate,
non-incomplete conservatism.
