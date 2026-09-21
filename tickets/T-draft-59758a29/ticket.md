---
id: T-draft-59758a29
title: frob.app.telemetry.redact_command now transitively loads frob.gates (T-1318
  boundary regression)
state: queued
kind: security
origin: human
created: '2026-09-21'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/telemetry/__init__.py
- tests/unit/security/test_redact.py
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
Found while burning down fresh CI run 35654510898 (dev tip a85fb35e12, re-verified failing on current dev tip too, e.g. in worktree at commit 26ddfe0f37). tests/unit/security/test_redact.py::TestRedactCommandImportGraph::test_calling_redact_command_never_loads_frob_gates and ::TestRedactModuleImportGraph::test_importing_redact_module_never_loads_frob_gates both fail: calling frob.app.telemetry.redact_command now loads 103 frob.gates.* modules into sys.modules. Root cause: redact_command's own docstring in src/frob/app/telemetry/__init__.py says it deliberately reuses frob.gates._secrets's _scan_line/_redact private helpers rather than re-deriving a second scanner -- but this test (T-1318's own named incident class: the security-critical redact boundary must never pull in the much heavier/broader frob.gates package, which itself is what did the CVE-relevant string in T-1318's incident) explicitly forbids exactly that reuse shape. Fix needs to either (a) extract the shared secret-scan primitives (_scan_line/_redact) out of frob.gates._secrets into a smaller shared module BOTH frob.gates._secrets and frob.app.telemetry can import without gates loading (mirroring frob.strata._effects's frob.vet._capability._PATTERNS reuse pattern this same docstring cites as precedent), or (b) confirm the test's own boundary is stale and update it with a stated reason -- do NOT just delete/skip the test.