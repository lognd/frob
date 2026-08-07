## Done report

Root cause: hypothesis (c), a python-side wiring bug in `src/frob/dup/_pipeline.py`'s
`_real_dataflow_graph`, not rust drift. `frob-core/src/lib.rs::wl_hash` is correct
(diffed byte-identical against every commit since 832494f; not touched). The R5
"real" graph builder filtered `block.children` down to a hardcoded
`_STATEMENT_NODE_LABELS` allowlist that assumed tree-sitter-python wraps simple
statements in an `expression_statement` node (`block > expression_statement >
assignment`). Dumping the actual `frob.lang.symbol_tree` output for the fixtures
showed this grammar never does that: `assignment` and bare `call` (e.g.
`print(x)`) appear as direct children of `block`, with no wrapper. Since
"assignment" was absent from `_STATEMENT_NODE_LABELS`, every assignment
statement was silently dropped from the def-use graph before it reached
`frob_core.wl_hash`; a function whose only surviving "statement" was its
trailing `return` collapsed to the same single-node graph as any other such
function, so unrelated functions (`unrelated_calc`, `double_plus_one`,
`impure_logger`, `impure_logger_dup`) WL-hash-collided into a false R5 match.
The paired "fires" test (`test_fires_on_reordered_dataflow_identical_functions`)
was passing for the wrong reason -- `combine_a`/`combine_b`'s two assignment
statements were both being dropped too, and only their identical trailing
`return p + q` was actually being compared.

Fix: `_real_dataflow_graph` now treats every direct child of `block` as a
statement (frob.lang's `export_tree` mirrors the tree-sitter node types
as-is, and `block`'s grammar rule only ever contains statement nodes -- no
filtering by label is needed or was ever correct). `_statement_ids` now
also recognizes a bare `assignment` node (`stmt.label == "assignment"`) in
addition to the previous `expression_statement > assignment` shape (kept
for robustness against other grammar builds). Deleted the now-dead
`_STATEMENT_NODE_LABELS` constant and updated the `_real_dataflow_graph`
docstring to record the corrected grammar assumption. This was NOT a
rust-source-drift regression from a later `frob-core` build as T-0091's
hypothesis framed it -- `_pipeline.py`'s R5 code is byte-identical (module
docstring path comments aside) all the way to the current tip of `main`
(453c5b3, ad23f62), so the bug has been live since R5 landed (cde4195/
0be4c9a) and was never caught because the fixture's specific shapes
happened not to expose it until this run.

T-0041 context: T-0041's "real CFG/DFG vs co-occurrence proxy" scope is
downstream of this fix, not overlapping it -- the def-use/control-flow
graph *shape* T-0041 wants is what `_real_dataflow_graph` already
attempts; this ticket only fixes which statements make it into that graph
in the first place.

Repro: fresh `uv sync` + `VIRTUAL_ENV=$(pwd)/.venv uvx maturin develop
--uv --release -m frob-core/Cargo.toml` in this worktree (which had no
`.venv` of its own -- created one; the worktree was pinned at d04e52f,
predating T-0091's Makefile VIRTUAL_ENV fix, which is itself still
`queued`, not landed, contrary to the dispatch brief's assumption).
`.so` verified byte-identical between `frob-core/target/release/
libfrob_core.so` and the installed `frob_core.abi3.so` (md5
75e1725b9f6645b84012af7a47325ae2) both before and after the fix.
`tests/test_dup_rungs.py::TestR5Dataflow::test_no_false_positive_against_unrelated_function`
reproduced FAILING pre-fix, PASSING post-fix, 5x repeated.

Evidence:
- tests/test_dup_rungs.py::TestR5Dataflow::test_no_false_positive_against_unrelated_function
- tests/test_dup_rungs.py::TestR5Dataflow::test_fires_on_reordered_dataflow_identical_functions

Tests: `uv run pytest tests/test_dup_rungs.py -q` -- 9 passed (was 8
passed, 1 failed pre-fix), fresh clean `frob-core` rebuild, fingerprint
cache cleared between runs. `uv run pytest -q tests/` (full suite,
frob-core AND strata-core both freshly built) -- all green, 2 skipped, 0
failures, 0 new relative to a stashed-fix rerun of the same suite.

Filed: none (T-0091 -- make core VIRTUAL_ENV fix -- and T-0092 -- cargo
test runner wiring -- both already existed and cover the two out-of-scope
gaps hit during this ticket: this worktree's `make core` still creates a
stray `strata-core/.venv` per T-0091's still-`queued` state, and
`cargo test --lib` for `frob-core` could not run here --
`libpython3.11.so.1.0` is absent from this environment's shared-library
path even with `LD_LIBRARY_PATH` pointed at `sysconfig`'s `LIBDIR`, which
only has `libpython3.10`. No rust code was touched by this ticket's fix
(frob-core/src/lib.rs unmodified, byte-identical .so before/after), so
this doesn't gate the fix, but it is the same class of gap T-0092 already
tracks.).

Gates: `frob check` clean, exit 0. Gate violation count unchanged by this
fix: 103 violation(s), 8 waived, both before (git-stashed) and after.
