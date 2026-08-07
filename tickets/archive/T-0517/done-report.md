## Done report

Changed:
src/frob/dup/_cache.py::_check_fingerprint
tests/unit/test_dup_cache.py::TestFingerprintInvalidation
tests/test_dup_cross_lang.py::_isolated_dup_cache

dup.db carried no version/algorithm invalidation key, so an untracked
leftover dup.db (or any dup.db written under an older frob/tree-sitter
grammar version) could silently serve stale fingerprint/verdict rows
after an algorithm change -- exactly the incident that made T-0494's
cross-lang R5 fixture flip results depending on which worktree ran it
(6 cache hits, 0 pairs verified). Reused the existing T-0243 fingerprint
mechanism from frob.graph.cache (`_compute_fingerprint`) rather than a
second implementation: `frob.dup._cache` now stores that same fingerprint
string in a `meta` table and wipes `fingerprints`/`verdicts` on any
mismatch, mirroring `frob.graph.cache._check_fingerprint`'s shape.

Also fixed the cross-lang test module (T-0517 part 2): `find_clones`
writes its cache to `snapshot.root/.frob/dup.db`, and `snapshot.root` for
`tests/test_dup_cross_lang.py` is the tracked fixture directory itself --
an unpatched run leaked `.frob/dup.db` straight into a tracked path. Added
an autouse fixture that monkeypatches `_cache._db_path` to redirect every
write in that module to `tmp_path`, plus a defensive cleanup of any
pre-existing leaked sidecar files.

Non-vacuous regression: `TestFingerprintInvalidation` in
tests/unit/test_dup_cache.py seeds a poisoned fingerprint row under a
monkeypatched wrong-version fingerprint, reconnects under the real
(current) fingerprint, and asserts the poisoned row is gone -- proving
`_check_fingerprint` actually invalidates rather than just existing.
A same-version reconnect case proves the common path does NOT wipe rows
it shouldn't.

Scope note: the ticket's prose named src/frob/dup/_legacy.py and
src/frob/dup/_pipeline.py, but the actual dup.db read/write/schema logic
lives in src/frob/dup/_cache.py (the YAML `scope:` field for this ticket
was empty/unset, so no glob restriction applied) -- _legacy.py has no
dup.db logic at all and did not need touching; _pipeline.py only
consumes _cache's get/put functions and needed no changes either.

### Changed
(no changed files detected)

### Evidence
- `tests/unit/test_dup_cache.py::TestFingerprintInvalidation::test_stale_fingerprint_row_is_not_served` (pytest node id, verified passing when recorded)
- `tests/unit/test_dup_cache.py::TestFingerprintInvalidation::test_matching_fingerprint_row_still_served` (pytest node id, verified passing when recorded)
