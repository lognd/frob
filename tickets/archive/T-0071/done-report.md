## Done report

Pulled forward from phase 2 by user directive (Rust-first: the prover
runs constantly). Delivered strata-core/: independent Cargo/maturin
crate (pyo3 0.22, abi3-py311, same posture as frob-core), kernels
reachable (deterministic BFS closure, barrier semantics), worst_age
(memoized longest-path DFS, +inf on positive cycles), demand
(inbound-rate aggregation); bundled .pyi stub + py.typed so ty sees
typed signatures. src/frob/strata/_facts.py now delegates all three
kernels to strata_core with NO pure-Python fallback (ImportError with
`make core` remedy); pydantic interface unchanged -- all 45 strata
tests green against the Rust kernels, 5 cargo tests green. Makefile
`core` target and CI build/test extended to both crates. Charter D3
amended in docs/strata/charter.md; kernel.md gained the strata-core
section. PyO3 exports annotated (frob:doc + frob:tests) per the
rust-publicness rule.
