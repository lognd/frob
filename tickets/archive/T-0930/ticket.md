---
id: T-0930
title: move audit-proven frob check hot paths to Rust in frob_core (maturin natives)
state: done
kind: feature
origin: human
created: '2026-07-26'
priority: high
blocked_by:
- T-0928
parent: T-0927
tier: ticket
sprint: null
scope:
- src/frob/graph/callgraph.py
- src/frob/graph/_core.py
- frob-core/src/lib.rs
- tests/test_graph.py
- tests/unit/graph/**
- docs/audits/check-performance.md
- docs/modules/graph.md
- docs/modules/dup.md
- frob-core/frob_core.pyi
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/**
  reason: 'narrow from repo-wide glob to the exact files touched: migrate callgraph
    resolve-edges hot loop (dead_symbols rust-candidate row) to frob_core, golden
    parity tests, audit-doc benchmarks'
  actor: logan
  at: '2026-07-27'
- op: add
  glob: src/frob/graph/callgraph.py
  reason: 'narrow from repo-wide glob to the exact files touched: migrate callgraph
    resolve-edges hot loop (dead_symbols rust-candidate row) to frob_core, golden
    parity tests, audit-doc benchmarks'
  actor: logan
  at: '2026-07-27'
- op: add
  glob: src/frob/graph/_core.py
  reason: 'narrow from repo-wide glob to the exact files touched: migrate callgraph
    resolve-edges hot loop (dead_symbols rust-candidate row) to frob_core, golden
    parity tests, audit-doc benchmarks'
  actor: logan
  at: '2026-07-27'
- op: add
  glob: frob-core/src/lib.rs
  reason: 'narrow from repo-wide glob to the exact files touched: migrate callgraph
    resolve-edges hot loop (dead_symbols rust-candidate row) to frob_core, golden
    parity tests, audit-doc benchmarks'
  actor: logan
  at: '2026-07-27'
- op: add
  glob: tests/test_graph.py
  reason: 'narrow from repo-wide glob to the exact files touched: migrate callgraph
    resolve-edges hot loop (dead_symbols rust-candidate row) to frob_core, golden
    parity tests, audit-doc benchmarks'
  actor: logan
  at: '2026-07-27'
- op: add
  glob: tests/unit/graph/**
  reason: 'narrow from repo-wide glob to the exact files touched: migrate callgraph
    resolve-edges hot loop (dead_symbols rust-candidate row) to frob_core, golden
    parity tests, audit-doc benchmarks'
  actor: logan
  at: '2026-07-27'
- op: add
  glob: docs/audits/check-performance.md
  reason: 'narrow from repo-wide glob to the exact files touched: migrate callgraph
    resolve-edges hot loop (dead_symbols rust-candidate row) to frob_core, golden
    parity tests, audit-doc benchmarks'
  actor: logan
  at: '2026-07-27'
- op: add
  glob: docs/modules/graph.md
  reason: 'narrow from repo-wide glob to the exact files touched: migrate callgraph
    resolve-edges hot loop (dead_symbols rust-candidate row) to frob_core, golden
    parity tests, audit-doc benchmarks'
  actor: logan
  at: '2026-07-27'
- op: add
  glob: docs/modules/dup.md
  reason: T-0930 also touches dup.md's shared frob-core kernel-list doc section since
    the new graph kernels register in the SAME pymodule
  actor: logan
  at: '2026-07-27'
- op: add
  glob: frob-core/frob_core.pyi
  reason: type stub update needed for the new frob_core functions (ty gate needs the
    stub to see resolve_call_edges/called_names/etc member signatures)
  actor: logan
  at: '2026-07-27'
evidence:
- tests/test_graph.py::TestResolveCallEdgesNative::test_native_matches_python_fallback_on_a_real_package
- tests/test_graph.py::TestResolveCallEdgesNative::test_native_matches_python_fallback_on_a_synthetic_edge_case
- tests/test_graph.py::TestResolveCallEdgesNative::test_core_available_true_dispatches_to_native_spy_and_false_does_not
designated_repro_test: null
threat: null
component: null
---
Child 3 of T-0927, blocked by the audit child. For rows the audit marks rust-candidate (CPU-bound tree-walking, hashing, scanning loops that survive the python quick wins), implement in the existing Rust natives (frob_core, built via frob natives build / maturin, T-0864 infra) with byte-identical python fallbacks when the native is unavailable (worktree-natives artifact pattern), golden parity tests python-vs-rust, and per-path before/after benchmarks in the audit doc. Narrow this ticket's scope to the specific files once the audit names them.