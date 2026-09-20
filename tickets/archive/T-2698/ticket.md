---
id: T-2698
title: 'LANG004: behavioral test_discovery coverage for rust/typescript/c/cpp/kotlin
  (cost-blocked, needs a bounded offline-safe fixture design)'
state: done
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
body_changes:
- mode: append
  reason: 'T-4709: preserve rust-migration measurement detail trimmed from _lang_conformance.py'
  actor: logan
  at: '2026-09-19'
  old_length: 1744
  new_length: 2840
evidence:
- tests/test_lang_conformance_gate.py::TestBehavioralCapabilityCheck::test_rust_test_discovery_is_behaviorally_checked
- tests/test_lang_conformance_gate.py::TestBehavioralCapabilityCheck::test_rust_test_discovery_passes_on_a_real_discoverable_fixture
- tests/test_lang_conformance_gate.py::TestBehavioralCapabilityCheck::test_rust_test_discovery_fails_when_the_crate_cannot_compile
- tests/test_lang_conformance_gate.py::TestBehavioralCapabilityCheck::test_test_discovery_is_not_behaviorally_checked_outside_python_and_rust
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 21cb414a74d34280f6a2861b12ab8348fe64abdc
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


T-4709 follow-up (condensed from _BEHAVIORALLY_CHECKED_CAPABILITIES's
comment block in src/frob/gates/_lang_conformance.py, trimmed for
DOCARCH002's 12-line cap): rust MOVED from the excluded set into
`_TEST_DISCOVERY_BUILDERS`/`_BEHAVIORAL_CAPABILITY_LANGUAGES` --
re-measured at ~0.9s cold (`cargo test --lib -- --list` on a two-file,
zero-dependency fixture crate, this repo's own environment; T-2682's
original ~2.3s figure was measured on a colder cargo registry cache)
and, critically, fully OFFLINE: the fixture crate declares no
dependencies, so `cargo test` never touches the network the way
typescript's `npm install` would. Bounded and offline-safe was exactly
the bar `_BEHAVIORAL_CAPABILITY_LANGUAGES`'s own prior comment asked a
future revisit to clear; rust clears it, the other three do not -- a
real, disclosed, COST-driven partial delivery (1 of 4 remaining), not a
forced uniform rollout. Revisit if/when a bounded, offline-safe way to
exercise them exists (e.g. a pre-built, checked-in fixture project per
toolchain instead of a from-scratch tmp-dir build every gate run).