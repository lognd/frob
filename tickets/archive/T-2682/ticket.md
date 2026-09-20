---
id: T-2682
title: 'LANG004: behavioral coverage for test_discovery (the last of 7 capabilities
  left structural-only)'
state: done
kind: feature
origin: human
created: '2026-08-19'
priority: medium
blocked_by:
- T-1599
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
  reason: 'T-4709: preserve per-toolchain cost detail trimmed from _lang_conformance.py'
  actor: logan
  at: '2026-09-19'
  old_length: 1316
  new_length: 2682
evidence:
- tests/test_lang_conformance_gate.py::TestBehavioralCapabilityCheck::test_implemented_capability_behaves_as_claimed[python-test_discovery]
- tests/test_lang_conformance_gate.py::TestBehavioralCapabilityCheck::test_test_discovery_is_not_behaviorally_checked_outside_python_and_rust
- tests/test_lang_conformance_gate.py::TestBehavioralCapabilityCheck::test_unchecked_capability_is_named_not_silently_true
designated_repro_test: null
evidence_changes:
- old_node: tests/test_lang_conformance_gate.py::TestBehavioralCapabilityCheck::test_test_discovery_is_not_behaviorally_checked_outside_python
  new_node: tests/test_lang_conformance_gate.py::TestBehavioralCapabilityCheck::test_test_discovery_is_not_behaviorally_checked_outside_python_and_rust
  reason: T-2698 renamed this test (rust joined the behaviorally-checked set); re-point
    T-2682's evidence to the renamed node in the same diff per the land-time OrphanedEvidenceDeletion
    guard
  actor: logan
  at: '2026-08-20'
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: adeff417ebafb723099fe65cf54a5622bf97d818
---
T-1599 extended LANG004's behavioral conformance suite to cover
call_graph/import_graph (both exercisable from a single-file fixture
via build_call_graph/extract_imports), leaving only test_discovery
structural-only. Unlike the other six capabilities, every _TEST_
DISCOVERY_COLLECTORS entry (frob.testing.collect_*_tests) shells out to
a real language toolchain (uv run pytest --collect-only, cargo test
--list, cmake/ctest, ...) rather than parsing source directly -- there
is no toolchain-free way to prove "this collector actually finds tests"
the way the other six capabilities can from one parsed file.

Scope: build a real per-language fixture PROJECT (not a single file) --
a minimal buildable/collectable layout per language (a pytest test
file, a cargo project with #[test], an npm project, a cmake+ctest
target, a kotlin gradle project) -- and extend
_BEHAVIORALLY_CHECKED_CAPABILITIES / _behavioral_capability_check to
invoke the real collector against it and assert the expected test node
id comes back. Needs a decision on acceptable CI cost/toolchain
availability (this gate runs in every frob check invocation, in every
adopter repo, so a slow/toolchain-fragile addition here has a much
wider blast radius than one repo's own test suite) -- flag that
tradeoff explicitly rather than just building it.


T-4709 follow-up (condensed from _BEHAVIORALLY_CHECKED_CAPABILITIES's
comment block in src/frob/gates/_lang_conformance.py, trimmed for
DOCARCH002's 12-line cap): measured directly while building this
(T-2682's own Done report has the numbers) -- `uv run pytest
--collect-only` on a throwaway fixture is ~10ms, cheap enough to run on
every `frob check` invocation the same way the other six capabilities
already do. cpp's collector only ever lists an ALREADY-CONFIGURED cmake
build directory (never invokes cmake itself) -- exercising it
behaviorally would mean this gate running `cmake` configure itself, a
second, heavier toolchain step. typescript's collector needs a `vitest`
dependency resolvable via `npx`; `npm install` in a tmp dir is a NETWORK
call, unacceptable for a gate that must stay fast and offline-safe.
kotlin's collector reads ALREADY-PRODUCED gradle JUnit reports (never
invokes gradle itself) -- producing one means a cold JVM + gradle
build, the heaviest of the four remaining.

`_BEHAVIORAL_CAPABILITY_LANGUAGES` is the language-scoped restriction
this required: `_BEHAVIORALLY_CHECKED_CAPABILITIES` alone means "check
this capability for every language with an IMPLEMENTED cell" (true and
fine for the other six, single-file-fixture-cheap regardless of
language) -- test_discovery is the first capability where that blanket
rule is wrong.