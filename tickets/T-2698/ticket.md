---
id: T-2698
title: 'LANG004: behavioral test_discovery coverage for rust/typescript/c/cpp/kotlin
  (cost-blocked, needs a bounded offline-safe fixture design)'
state: queued
kind: feature
origin: human
created: '2026-08-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_lang_conformance.py
- tests/test_lang_conformance_gate.py
- docs/modules/lang.md
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
T-2682 extended LANG004's behavioral test_discovery check to python
only (a real fixture pytest project, ~10ms measured), leaving rust/
typescript/c/cpp/kotlin structural-only on purpose --
_BEHAVIORAL_CAPABILITY_LANGUAGES restricts dispatch. Measured per-
toolchain cost that ruled the other five out this round:

- rust: cargo test --lib -- --list on an empty fixture crate is a cold
  ~2.3s (rustc compiles it first, no cache benefit from a fresh tmp dir).
- cpp: collect_cpp_tests only lists an ALREADY-CONFIGURED cmake build
  dir (never invokes cmake itself, per its own docstring) -- exercising
  it behaviorally would mean this gate running cmake configure itself,
  a second toolchain step.
- typescript: collect_ts_tests needs npx vitest resolvable, which means
  npm install in the fixture -- a network call, not acceptable in a
  gate that must stay fast and offline-safe.
- kotlin: collect_kotlin_tests reads ALREADY-PRODUCED gradle JUnit
  reports (never invokes gradle itself) -- producing one means a cold
  JVM + gradle build, the heaviest of the five.

Scope: find a bounded, offline-safe way to exercise these five
behaviorally without paying full toolchain cost on every frob check
invocation -- candidates worth evaluating: a pre-built, checked-in
fixture project per toolchain (compiled/configured once, committed,
re-verified only when the fixture itself changes rather than on every
gate run); an opt-in slow stage separate from gates-fast; or caching
the toolchain artifact keyed on fixture content hash the way
collect_rust_tests/collect_python_tests already cache their own real
collection. Needs an explicit owner decision on acceptable CI cost --
this is a design tradeoff, not a straightforward implementation gap.
