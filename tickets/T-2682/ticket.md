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
evidence:
- tests/test_lang_conformance_gate.py::TestBehavioralCapabilityCheck::test_implemented_capability_behaves_as_claimed[python-test_discovery]
- tests/test_lang_conformance_gate.py::TestBehavioralCapabilityCheck::test_test_discovery_is_not_behaviorally_checked_outside_python
- tests/test_lang_conformance_gate.py::TestBehavioralCapabilityCheck::test_unchecked_capability_is_named_not_silently_true
designated_repro_test: null
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