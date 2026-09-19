---
id: T-draft-8608927d
title: 'Rust base plus pyo3-bridge, cargo-bin and cargo-lib facets: rust-tool and
  rust-library become reachable'
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: high
blocked_by:
- T-4766
parent: T-4757
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/scaffold/data/bases/rust/**
- src/frob/scaffold/data/facets/pyo3-bridge/**
- src/frob/scaffold/data/facets/cargo-bin/**
- src/frob/scaffold/data/facets/cargo-lib/**
- src/frob/scaffold/data/types/pyo3-library/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: Given the rust-tool preset, when it is rendered, then cargo test passes in
    the rendered tree
  evidence: []
- text: Given the pyo3-library preset, when its rendered frob.toml is compared against
    the python base's, then it is the same file, not a fork
  evidence: []
- text: Given rust-tool, rust-library and pyo3-library, when frob check runs in the
    rendered trees, then it is clean
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Introduce the rust BASE and make pure Rust reachable.

Today pyo3-library is the ONLY Rust path, and it forces a Python wrapper on
anyone who wants a Rust binary or crate. Its pyproject is 84 percent a
duplicate of the shared python one, its CI workflow 67 percent, and its
frob.toml 82 percent -- and the fork dropped the refs block, which is why it
reports 11 REF001.

1. rust base: Cargo manifest, the toolchain file, clippy denying warnings,
   cargo test, frob.toml with a rust test runner.
2. pyo3-library becomes rust plus python plus a pyo3-bridge facet plus
   github-ci plus release-ci -- no forked python files.
3. rust-tool: rust plus a cargo-bin facet (a main module with an argument
   parser) plus release-ci building per-platform binaries.
4. rust-library: rust plus a cargo-lib facet plus release-ci publishing to
   the crate registry.

Positive controls:
1. rust-tool renders and its cargo test passes in the rendered tree;
2. pyo3-library's rendered frob.toml is the python base's, asserted by
   comparison, so the fork cannot silently return;
3. frob check clean on all three presets.
