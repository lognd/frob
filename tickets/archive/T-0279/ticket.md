---
id: T-0279
title: frob:tests directive src/target direction disagrees between fresh dsl parse
  and stale graph cache
state: done
kind: bug
origin: human
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/graph/**
- src/frob/gates/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: condense schema-bump history into T-0279 body, keep invariant in code
  actor: logan
  at: '2026-09-19'
  old_length: 1832
  new_length: 4435
evidence:
- tests/test_graph.py::TestCacheModule::test_tests_edge_direction_agrees_fresh_parse_vs_cache_roundtrip
- tests/test_graph.py::TestCacheModule::test_schema_version_mismatch_wipes_derived_rows
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while working T-0259: a fresh frob.graph.dsl.parse_directives call on a frob:tests comment placed above a SOURCE symbol (the _conform.py/_generate.py convention) produces Edge(src=<source symbol>, target=<test id text>). But frob.gates._test_edges groups TESTS edges by edge.target, and _test001_002_one looks up unit_edges.get(record.symref) where record.symref is the SOURCE symbol -- these can never match for a freshly-parsed file. Confirmed empirically: a direct parse_file+parse_directives call on the real, unchanged src/frob/deploy/_generate.py reproduces src=source/target=test (the 'broken' shape), while the live GraphSnapshot's cached edges for that same unchanged file come back reversed (src=test/target=source, the 'working' shape) -- meaning the .frob/cache.db entry for that file predates a src/target semantic change in the current dsl.py/gates code and is silently masking the mismatch by never being invalidated. New frob:tests directives placed above SOURCE symbols (matching every existing precedent in the repo) get spurious TEST001 violations; placing the directive above the TEST method instead with the source symref as target works around it (see T-0259's Done report) but is not documented anywhere as the required convention, and every existing source-side directive in the repo is only 'passing' by cache accident. Fix: either (a) make dsl.py's TESTS-kind edge construction match gates.py's consumption (swap src/target, or attach the comment differently), and force a cache-format bump so all existing cached entries reparse under the corrected semantics, or (b) fix gates.py's lookup to match dsl.py's actual output and same cache-bump concern. Either way this needs a full cache invalidation to reveal how many of the repo's existing frob:tests directives are actually silently non-functional.

<!-- narrative-moved:src/frob/graph/cache.py:71:T-0279 -->
frob:ticket T-0279
Bumped 1 -> 2: a cache.db written before the T-0336 gates.py fix (which
taught `frob.gates` to treat a `frob:tests` edge's src/target endpoints
per the either-direction convention, T-0137) can carry rows whose shape
was never re-validated against that convention -- `_check_fingerprint`
only catches a PACKAGE VERSION change, not a same-version code fix inside
a dev/editable install (`_FINGERPRINT_PACKAGES` reads `importlib.metadata`
versions, which do not move between commits absent an explicit version
bump). `dsl.py`'s fresh-parse construction (`src`=attached symbol,
`target`=directive argument, always) and `cache.py`'s store/load
(identity passthrough, no field swap) already agree with each other --
this bump exists purely to force every existing `.frob/cache.db` in the
wild to discard whatever it holds and reparse once under the current,
canonical dsl.py+gates.py pairing, rather than trusting rows written
under an unknown historical version of that pairing forever.
frob:ticket T-0245
Bumped 2 -> 3: the `files` table gains `mtime_ns`/`size` columns (T-0245):
a mount-filesystem stat is one syscall vs. the open+read+close of a full
content hash, so build_graph and load_graph can trust an unchanged
(mtime_ns, size) pair and skip reading file bytes entirely for the common
"nothing changed" case -- the per-file stat storm this ticket exists to
cut. A cache.db written under schema 2 has no such columns, so this must
invalidate it same as any other shape change.
frob:ticket T-1464
Bumped 3 -> 4: new `parsed_artifacts` table (T-1464) persists whole
per-file `ParsedFile` payloads (symbols/comments/content_hash), keyed by
`(content_hash, fingerprint)`, so `ProcessPoolExecutor` gate workers
(perf/dup/dead_symbols/arch, see `frob.gates._run_process_gate`) can read
an already-derived artifact instead of independently re-parsing +
re-extracting the same file in every worker process. Lives in this same
`connect()`/schema machinery but under its OWN db file
(`.frob/parse-artifacts.db`, `frob.gates._PARSE_ARTIFACT_CACHE_REL`) --
NOT `.frob/cache.db` -- so this table's write volume never contends
with `store_file_data`'s own T-1423 lock budget on the graph-snapshot
cache; this schema bump still applies to BOTH files (any db this
module's `connect()` ever opens gets the new table). A db written
before this table existed has no such rows -- same "shape changed, must
invalidate" rule as every prior bump, even though this bump is additive
(no existing table's columns changed) rather than corrective.