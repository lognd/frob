---
id: T-3677
title: 'refactor split: multi-symbol chunk each needing a distinct carry-forward import
  into the same pre-existing dest block overlaps'
state: queued
kind: bug
origin: human
created: '2026-09-01'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/refactor/_scan_carry.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while dogfooding frob refactor split for T-3642's LARGE001 split of _scan.py. T-3645's needed_import_ops_for_symbols fix merges a carried-forward import into dest_file's existing top-of-file import block via a REPLACE RewriteOp targeting that block's own [start_line, end_line] span. When TWO OR MORE symbols in the SAME split chunk each independently need a DIFFERENT import carried into that SAME already-populated destination block, each symbol's own build_plan call computes its own merge op against the pre-chunk file state -- both land on the IDENTICAL [start_line, end_line] span (the block has not grown yet, since planning for every symbol in a chunk happens before any of the chunk's ops apply), and apply_plan's OverlappingRewrites guard correctly refuses the chunk rather than silently clobbering one op with the other. Repro: split 10 helper symbols from src/frob/refactor/_scan.py into frob.refactor._scan_carry in one default-chunk-size(5) call, where two symbols in the second chunk (needed_import_ops_for_symbols, stale_dest_import_ops) each independently need imports carried into the by-then-existing _scan_carry.py top block -- refused with OverlappingRewrites. Workaround used: --chunk-size 1. Suggested fix: extend _split.py's own _dedupe_equivalent_import_ops (or a sibling pass) to also collapse/merge same-file same-span MERGE ops (not just the old append-style ones _import_name_set already recognizes) -- e.g. detect two ops on the identical [start,end] span whose old_text matches (same pre-chunk block) and combine their appended new lines into one op instead of refusing.