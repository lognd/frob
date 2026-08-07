## Done report

Changed:
src/frob/graph/cache.py::_FINGERPRINT_PACKAGES
src/frob/graph/cache.py::_compute_fingerprint
src/frob/graph/cache.py::_check_fingerprint
src/frob/graph/cache.py::connect
tests/test_graph.py::TestBuildIncremental.test_fingerprint_bump_rebuilds

Added a `meta.fingerprint` row to `.frob/cache.db`, computed from the
installed `frob` package version plus the tree-sitter/grammar package
versions (`tree-sitter`, `tree-sitter-python`, `tree-sitter-cpp`,
`tree-sitter-language-pack`) via `importlib.metadata.version`. `connect()`
now compares the stored fingerprint against the current one on every open;
on mismatch it deletes all derived rows (`files`, `symbols`, `edges`,
`malformed`) and the stored `root` key (mirroring the existing
schema-version-mismatch recovery path), then writes the new fingerprint.
This forces `build_graph` to treat every file as a cache miss and reparse
from scratch, and forces `load_graph` to see "never been built"
(`GraphError.CacheCorrupt`) instead of silently returning an emptied-out
but `Ok` snapshot. Schema-version invalidation (`_SCHEMA_VERSION`) is
untouched and remains a separate, independent check.

Evidence: `tests/test_graph.py::TestBuildIncremental::test_fingerprint_bump_rebuilds`
monkeypatches `graph_cache._compute_fingerprint` to a fake value, builds a
2-file tree (parsed=2, cache_hits=0), rebuilds under the same fake
fingerprint (parsed=0, cache_hits=2 -- normal cache-hit path still works),
then rebuilds again after bumping the fake fingerprint to a different fake
value and asserts a fully cold rebuild (parsed=2, cache_hits=0). Ran via
`uv run pytest tests/test_graph.py -q` (all passing, no new failures) and
the full suite via `make coverage` (2957 tests, all passing).

Filed: none (no out-of-scope work found; the schema-version wipe path this
mirrors already existed).

Gates: `uv run frob check --delta --ticket T-0243` clean -- 0 errors, 44
new warnings (all pre-existing waived categories, none new/unwaived) after
`make coverage` re-stamped coverage and `frob ticket sweep T-0243`
refreshed the pre-work sweep. No waivers added by this change.
