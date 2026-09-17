---
id: T-4554
title: 'T-4536 regression: tests/unit/strata/test_effects.py::TestExtendedKindsDriftLock::test_extended_kinds_is_disjoint_from_kind_map
  fails on dev (_PATTERNS/_KIND_MAP/_EXTENDED_KINDS drift from the C# resolver)'
state: in-progress
kind: bug
origin: agent
created: '2026-09-17'
priority: high
parent: T-4513
tier: ticket
sprint: v0.533.0
runs_last: false
milestone: v0.533.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/vet/_capability_registry/_dangerous_ops_bash_csharp.py
- tests/unit/strata/test_effects.py
- src/frob/vet/_capability_registry/_unity_api.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/strata/_effects.py
  reason: fix confined to _dangerous_ops_bash_csharp.py and test_effects.py; _effects.py
    leased by T-draft-d56bad34
  actor: logan
  at: '2026-09-17'
- op: add
  glob: src/frob/vet/_capability_registry/_unity_api.py
  reason: 'TestExtendedKindsDriftLock fails: T-4514''s UnityWebRequest/WWW/NetworkManager/Application.OpenURL
    entries use the bare retired capability_kind=net; recategorize to net-connect,
    consistent with the rest of the registry'
  actor: logan
  at: '2026-09-17'
designated_repro_test: null
acceptance:
- text: GIVEN dev WHEN tests/unit/strata/test_effects.py runs THEN TestExtendedKindsDriftLock
    passes
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured 2026-09-17 by the T-4495 implementer: 1 failure in tests/unit/strata/test_effects.py, TestExtendedKindsDriftLock::test_extended_kinds_is_disjoint_from_kind_map, traced to T-4536 (C# capability resolver) adding entries to _PATTERNS whose kinds overlap _EXTENDED_KINDS and _KIND_MAP. Fix the registry entries (or the drift lock) so the invariant holds; no behaviour change to the resolver.