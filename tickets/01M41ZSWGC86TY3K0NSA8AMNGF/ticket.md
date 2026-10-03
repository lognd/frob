+++
id = "01M41ZSWGC86TY3K0NSA8AMNGF"
title = "Warm frob check re-does graph (3.0 s) and directives (2.2 s) on an unchanged repository"
type = "bug"
category = "todo"
priority = "high"
points = 3
reporter = "lognd"
created = "2026-10-03T22:57:51Z"
updated = "2026-10-03T22:57:54Z"
scope = ["crates/frob-check/src/**", "crates/gob-cache/**", "crates/gob-symbols/src/pipeline.rs", "crates/gob-directives/src/**", "crates/frob-check/tests/warm_cache.rs"]

[[acceptance]]
text = "Given an unchanged fixture repository, when frob check runs twice, then the second run extracts zero files in the graph and directives stages"
bound = false

[[acceptance]]
text = "Given this repository in a release build, when check runs warm, then the report gives cold and warm totals before and after the fix"
bound = false
+++

Measured 2026-10-03 (debug build, warm run right after a cold run on this repository, nothing changed in between), frob check stage timings: walk 273 ms, graph 2969 ms, directives 2205 ms, ledger 78 ms, file-rules 620 ms, everything else under 60 ms. On a warm cache with no file changed, graph and directives should be near zero: the architecture's warm path (architecture.md 9, budget under 2 s on 100k lines in release) is cache hits keyed by content digest. Find out why: whether the directive scan and the symbol graph are cached per file at all, whether the cache key changes between runs (absolute paths, timestamps, ordering, a config digest), or whether a cache hit still deserializes and rebuilds the whole graph. Fix the cause, add a regression test that a second run on an unchanged fixture repository re-extracts zero files in both stages (stats already count graph_extracted and cached), and report release-build cold and warm totals on this repository before and after.
