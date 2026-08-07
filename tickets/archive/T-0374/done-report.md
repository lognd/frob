## Done report

Changed:
- src/frob/gates/_filehash.py (new) -- `_sha_of`, `_walk`, `_collect_file_hashes`, the one home for the shared file-walk+hash body
- src/frob/gates/_coverage.py -- drops its local `_sha_of`/`_walk`/`_collect_file_hashes` copies, imports from `frob.gates._filehash`
- src/frob/gates/_baseline.py -- same: drops its local copies, imports from `frob.gates._filehash`

The two copies were byte-identical (walk body, `_SOURCE_EXTS`, exclude set, hash algorithm) -- no semantic reconciliation was needed. `_filehash._sha_of` further delegates to `frob.graph`'s existing `_content_hash` (same sha256-over-bytes primitive `build_graph`'s incremental cache already uses) rather than a third hand-rolled copy of that one-liner, which `frob-dup` flagged as a new 6-line duplicate against `frob.graph.__init__` on the first pass -- fixed by delegating instead of waiving. `_filehash.py` kept its three symbols private (leading underscore, no `__all__`) since it is an internal implementation detail of the two stamp modules, not a standalone public gate surface -- this also sidesteps COV001/TEST001/frob-exports obligations that would otherwise apply to a new public module. Widened T-0374's scope to include the new `src/frob/gates/_filehash.py` file (re-swept via `frob ticket sweep T-0374`) since the shared-module extraction plan named in this ticket's own body requires a file outside the two originally-scoped paths.

Evidence: 7 pytest node ids recorded via `frob ticket evidence T-0374` (see `evidence:` above) -- `TestBaselineDelta` round-trip/staleness tests and `TestCoverageLoad` stamp-roundtrip/join tests, all exercising `_collect_file_hashes`/`_sha_of` indirectly through `stamp_baseline`/`stamp_coverage`/`is_baseline_stale`/`load_coverage`.

Filed: none (no out-of-scope work found).

Gates: `uv run frob check --ticket T-0374` clean (0 errors, 1 pre-existing warning, 41 waived -- all pre-existing debt, none new). `uv run frob check --only dup` dropped from 1 unaccounted group (the new `_filehash` vs `frob.graph` pair, fixed by delegation) to 0 unaccounted groups (122 waived, unrelated pre-existing waivers) -- the original T-0364/T-0374 baseline/coverage dup pair is gone for real, not waived. `uv run frob test --base main` passed (touched-set selection ran `tests/test_gates.py::test_gates_run_gates_integration`, exit=0). `uv run pytest tests/test_gates.py` -- 165 passed.
