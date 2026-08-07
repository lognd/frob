## Done report

T-1217 investigated but could not be implemented as scoped (gates/__init__.py
+ check/__init__.py only); re-filed as T-1464 with a scope that actually
reaches the fix: src/frob/lang (parse_file/iter_identifiers), src/frob/graph
(the sqlite cache), and design/frob.strata + docs/modules/graph.md for the
capability/doc updates.

Implemented a content-hash-keyed persistent parse-artifact table in
src/frob/graph/cache.py (store_parsed_artifact/load_parsed_artifact),
alongside the existing files/symbols/edges tables, and wired
src/frob/lang/__init__.py's parse_file to consult it before re-parsing/
re-extracting: a cache hit in a fresh ProcessPoolExecutor worker now skips
the walk entirely instead of paying the full per-worker cold-cache cost
frob.check._memo.run_memo_scope's single-process thread-pool coverage never
reached. A locked/unavailable cache degrades to a plain miss (load) or a
silent no-op (store) rather than raising, matching cache.db's existing
lock-degradation posture elsewhere in this module.

design/frob.strata: SELFAUDIT001 capability declarations for the new
lang.os.environ read this fix introduces, plus the 2 new test symbols.
docs/modules/graph.md: AFFECT001 doc for store_parsed_artifact/
load_parsed_artifact/parse_file's affects()-closure, documenting the new
persistent parse-artifact cache mechanism.

Verification: pytest on tests/unit/test_graph_cache.py (4, new),
tests/unit/test_lang_artifact_cache.py (5, new), tests/test_graph.py (127),
tests/test_graph_lock.py (18) -- all passing, foreground, both before and
after this session's `git merge main` (re-ran post-merge and post-`make
core` to confirm the merge did not regress anything).

Filed T-1489 (WIRE001 false positive: text-scan misses
memoize_per_run(_target)-shaped wiring -- frob.lang._parse_file_with_
artifact_cache's only production reference is memoize_per_run-wrapped,
which WIRE001's independent text scan does not recognize as reached the
way frob.graph.callgraph._called_names' T-0583 wrapper-marker allowance
already does) as a follow-up, out of this ticket's own scope.

Land-repair note (this session, coordinator dispatch): this Done report and
the evidence binding above were written during land-repair after the
original implementing session's work was found uncommitted in the worktree
with no evidence/Done report ever persisted to tickets.md -- the code
(src/frob/lang/__init__.py, src/frob/graph/cache.py, design/frob.strata,
docs/modules/graph.md, src/frob/gates/__init__.py, the two new test files)
was committed here, main was merged in cleanly, `make core` rebuilt natives,
and the full test set above was re-verified passing before recording
evidence and this report.

### Changed
```
 design/frob.strata                     |  13 +-
 docs/modules/graph.md                  |  49 +++++++
 src/frob/gates/__init__.py             | 101 +++++++++++++-
 src/frob/graph/cache.py                |  83 +++++++++++-
 src/frob/lang/__init__.py              | 238 ++++++++++++++++++++++++++++++++-
 tests/unit/test_graph_cache.py         |  65 +++++++++
 tests/unit/test_lang_artifact_cache.py | 117 ++++++++++++++++
 tickets.md                             |  79 ++++++++++-
 8 files changed, 733 insertions(+), 12 deletions(-)
```

### Evidence
- `tests/unit/test_graph_cache.py::TestParsedArtifacts::test_store_then_load_round_trips` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_cache.py::TestParsedArtifacts::test_load_miss_returns_none` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_cache.py::TestParsedArtifacts::test_different_fingerprint_is_a_separate_key` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_cache.py::TestParsedArtifacts::test_store_overwrites_existing_payload` (pytest node id, verified passing when recorded)
- `tests/unit/test_lang_artifact_cache.py::TestParseFileArtifactCache::test_no_env_is_a_transparent_passthrough` (pytest node id, verified passing when recorded)
- `tests/unit/test_lang_artifact_cache.py::TestParseFileArtifactCache::test_miss_populates_cache` (pytest node id, verified passing when recorded)
- `tests/unit/test_lang_artifact_cache.py::TestParseFileArtifactCache::test_hit_skips_extract` (pytest node id, verified passing when recorded)
- `tests/unit/test_lang_artifact_cache.py::TestArtifactCacheLockDegradesGracefully::test_load_locked_is_treated_as_a_miss` (pytest node id, verified passing when recorded)
- `tests/unit/test_lang_artifact_cache.py::TestArtifactCacheLockDegradesGracefully::test_store_locked_does_not_raise` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: 1 error(s), 1188 warning(s), 750 waived
- error-findings: PRE001@tickets/T-1464
