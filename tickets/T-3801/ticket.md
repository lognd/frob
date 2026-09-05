---
id: T-3801
title: skip rust/cargo behavioral capability checks on win32 (no libpython path)
state: in-progress
kind: bug
origin: human
created: '2026-09-05'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_lang_conformance_gate.py
- src/frob/testing/_runners.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/testing/_runners.py
  reason: investigate a real platform-aware cargo_env fix instead of a skip, per user
    request
  actor: logan
  at: '2026-09-05'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
3 rust/cargo tests fail on win32: TestBehavioralCapabilityCheck::test_implemented_capability_behaves_as_claimed[rust-test_discovery], test_rust_test_discovery_passes_on_a_real_discoverable_fixture, TestCapabilityConformanceGate::test_real_registry_is_behaviorally_clean. Root cause: src/frob/testing/_runners.py's _cargo_env builds an LD_LIBRARY_PATH overlay for the PyO3 cargo subprocess to find libpython -- LD_LIBRARY_PATH is a POSIX-only dynamic-linker env var with no Windows equivalent (Windows resolves DLLs via PATH, and python3XX.dll/.lib discovery for PyO3 on Windows is a materially different mechanism not implemented here), so _cargo_env's libpython resolution is genuinely unsupported on win32 today. Skip the 3 rust-cargo tests on win32 rather than faking a fix; a real win32 PyO3 cargo_env implementation is a separate, larger undertaking (file follow-up if pursued). Part of win32 CI drain.