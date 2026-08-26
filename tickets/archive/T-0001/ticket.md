---
id: T-0001
title: frob-core PyO3/maturin crate + smart dup (Phase 7)
state: done
kind: feature
origin: human
created: '2026-07-17'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/dup/**
- frob-core/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'T-2993: prove archived-ticket body-append route before any narrative-migration
    batch'
  actor: logan
  at: '2026-08-26'
  old_length: 1066
  new_length: 1285
evidence:
- tests/test_dup_rungs.py::TestR4NearMiss::test_fires_on_gapped_clone
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Phase 7 (0.2.0), designed in docs/modules/dup.md: frob-core PyO3/maturin crate (R3 canonicalizer, winnowing, LSH, WL-kernel, APTED; compute-only, no-Python-fallback, lithos as build reference); region-granular matching (function/subsection); content-addressed fingerprint + LRU verdict caches in .frob/dup.db; DUP001/DUP002 gates; R6 observational probing via frob.fuzz generators; pre-work sweep re-platformed onto it.

PARTIAL (T-0037): frob-core built + R1/R2/R3 + DUP gate shipped.
Remaining: R4 (winnowing/LSH orchestration), R5 (WL-kernel), R6
(observational probing), region-subsection matching, cache-in-hot-path.

RUNGS COMPLETE (worktree agent): R4 (winnow+candidate+tree-edit),
R5 (WL-hash Rust kernel + co-occurrence proxy graph), R6
(probe_equivalence real for pure Python pairs via frob.fuzz
generators), region-subsection spans, cache in hot path (fixed a
pre-existing PK bug). 8/8 cargo tests, 16 Python rung tests.
Follow-on only: --probe CLI flag exposure; full APTED (currently
statement-Levenshtein); real CFG/DFG (currently co-occurrence proxy).

T-2993 archived-write-path proof (T-2678 route): this note confirms `frob ticket body --append-file` on an archived ticket writes only the archive path and does not create a duplicate active tickets/T-0001 directory.