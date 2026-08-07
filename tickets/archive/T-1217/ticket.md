---
id: T-1217
title: 'perf: process-pool gate workers re-derive per-file artifacts -- persist derived
  artifacts keyed by content hash'
state: dropped
kind: feature
origin: agent
created: '2026-07-29'
priority: high
parent: T-1204
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
- src/frob/check/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: 'GIVEN _run_process_gate (gates/__init__.py:6050) has no run_memo_scope or
    shared parse artifacts, so perf/clones/dead_symbols/sys/pii/arch each independently
    re-parse+re-extract the whole repo in their own worker (perf 38 pct, clones 69
    pct, dead_symbols 88 pct -- the single biggest summed cost in the run, ~25-30s
    native) WHEN derived per-file artifacts (body tokens, leaf identifiers, comment/docstring
    spans, import specs) are persisted keyed by the content hash already stored in
    cache.db, and parse_file/extract consult that table before re-walking THEN warm-run
    stage time for perf/clones/dead_symbols/sys drops by the dominant share of their
    current native cost (report candidate #10)'
  evidence: []
threat: null
component: null
---
Root cause: gates/__init__.py:6050 _run_process_gate ships gates to a ProcessPoolExecutor with no run_memo_scope and no shared parse-artifact cache, unlike check/__init__.py:612 which wraps thread stages with memoization. Each pool worker re-parses and re-extracts the whole repo independently. Fix (Python-side, precedes any Rust migration): persist derived per-file artifacts (body tokens, leaf identifiers, comment/docstring spans, import specs) in a sqlite table keyed by the content hash already in cache.db; parse_file/extract read this table instead of re-walking trees. This is the single largest summed cost in the profile and should land before or alongside EPIC B's Rust migration, not instead of it -- Rust makes the per-artifact compute cheaper, this ticket stops it from being redone N times.

## Drop reason
- 2026-08-04: Superseded by T-1464: T-1217's declared scope cannot structurally reach the real fix; T-1464 carries the implementation and evidence