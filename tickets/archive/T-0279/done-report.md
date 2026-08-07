## Done report

Root-cause re-confirmed: dsl.py's fresh-parse construction (src=attached
symbol, target=directive argument) and cache.py's store/load (identity
passthrough, no field swap) ALREADY agree with each other and with gates.py
under the current code (post T-0336/T-0137 either-direction convention). The
only remaining hazard is STALE .frob/cache.db files written under an older
dsl.py/gates.py pairing, which _check_fingerprint cannot catch (it keys on
importlib.metadata package VERSION, which does not move between commits in a
dev/editable install absent an explicit bump).

Fix: bumped src/frob/graph/cache.py::_SCHEMA_VERSION 1 -> 2 so every existing
cache in the wild discards its rows and reparses once under the canonical
pairing -- the honest, minimal fix (no src/target transform needed, since
the two paths already agree; the disagreement was purely fresh-vs-stale-cache,
not fresh-vs-cache-logic).

Evidence (2 tests, pass): test_tests_edge_direction_agrees_fresh_parse_vs_cache_roundtrip
writes a source-side frob:tests directive, parses fresh, round-trips through
cache store/load, and asserts src/target are identical (no swap) -- proving
the two paths agree; test_schema_version_mismatch_wipes_derived_rows proves a
cache written under an older schema version is discarded on load. Coordinator
finalized (implementer stalled on a block-and-stall background frob test wait,
T-0322; verified both tests pass on current main). Landed via 3-way patch.
