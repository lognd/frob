---
id: T-2797
title: extend the parse-artifact disk cache to persist extract()'s output, not just
  the raw parse
state: queued
kind: feature
origin: human
created: '2026-08-21'
priority: high
parent: T-2790
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/lang/__init__.py
- tests/unit/test_memo.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 92e6cc708c9c59f2655664d36690d267e85ea6c7
---
T-2790's profile found the SAME structural gap independently in both perf
(59.63s stage) and dead_symbols (34.08s stage): both call
frob.lang.parse_file on every file, get a cheap hit on the persistent,
content-hash-keyed sqlite parse-artifact cache (T-0414) for the raw
tree-sitter parse, and then still pay the full extract() symbol/comment
walk cost -- measured 85.07s (perf, 29% of its own profiled time) and
87.51s (dead_symbols, 30%) -- because extract()'s output is only memoized
via @memoize_per_run (T-0423/T-0410), a process-lifetime, in-memory-only
cache. Every gate here is dispatched as its own OS process
(_ProcessJob in src/frob/gates/__init__.py), so the process that ran
build_graph()'s own parse_file/extract() calls (populating that in-memory
memo) has already exited by the time perf's or dead_symbols' own process
starts -- each pays the extract() cost again, redundantly, from scratch.

Plan: extend _parse_file_with_artifact_cache's sqlite-backed,
content-hash-keyed payload to also persist extract()'s structured
output (not just the raw parse), so any process -- not just the one that
computed it first -- gets a real cache hit. Content-hash-keyed, so this
is a pure caching change with no soundness implication: the cached value
is a deterministic pure function of file content, identical to computing
it fresh.

Hard requirements per T-2790's own constraints:
- A positive control: change one file's content, confirm its cache entry
  is invalidated (new content hash) and the fresh extraction is correct
  -- prove this is NOT a staleness bug waiting to happen.
- A real, unbudgeted frob check run on this repo must report an
  IDENTICAL finding count before and after.
- No silent caps -- if the cache ever falls back to recomputing (e.g. a
  schema version bump invalidates old entries), log it.

See docs/investigations/T-2790-check-stage-profile.md for the full
profile (perf and dead_symbols sections) this ticket is drawn from.

## Failure log
- 2026-08-21 attempt 1: premise falsified: _parse_file_with_artifact_cache (T-1464) already persists extract()'s full ParsedFile output to disk, tested and confirmed working (27.25s warm vs 42.69s cold dead_symbols); remaining redundancy is a build_graph-runs-before-cache-stamp + concurrent-wave-race issue in src/frob/gates/__init__.py, outside this ticket's lang/__init__.py-only scope -- filed as T-2806
