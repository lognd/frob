---
id: T-5215
title: frob.app.telemetry.redact_command now transitively loads frob.gates (T-1318
  boundary regression)
state: in-progress
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
body_changes:
- mode: append
  reason: corrected root cause after tracing python -X importtime; original diagnosis
    (redact_command's own body) was wrong
  actor: logan
  at: '2026-09-21'
  old_length: 1406
  new_length: 3183
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5215
branch: t-5215
---
Found while burning down fresh CI run 35654510898 (dev tip a85fb35e12, re-verified failing on current dev tip too, e.g. in worktree at commit 26ddfe0f37). tests/unit/security/test_redact.py::TestRedactCommandImportGraph::test_calling_redact_command_never_loads_frob_gates and ::TestRedactModuleImportGraph::test_importing_redact_module_never_loads_frob_gates both fail: calling frob.app.telemetry.redact_command now loads 103 frob.gates.* modules into sys.modules. Root cause: redact_command's own docstring in src/frob/app/telemetry/__init__.py says it deliberately reuses frob.gates._secrets's _scan_line/_redact private helpers rather than re-deriving a second scanner -- but this test (T-1318's own named incident class: the security-critical redact boundary must never pull in the much heavier/broader frob.gates package, which itself is what did the CVE-relevant string in T-1318's incident) explicitly forbids exactly that reuse shape. Fix needs to either (a) extract the shared secret-scan primitives (_scan_line/_redact) out of frob.gates._secrets into a smaller shared module BOTH frob.gates._secrets and frob.app.telemetry can import without gates loading (mirroring frob.strata._effects's frob.vet._capability._PATTERNS reuse pattern this same docstring cites as precedent), or (b) confirm the test's own boundary is stale and update it with a stated reason -- do NOT just delete/skip the test.

CORRECTED ROOT CAUSE (investigated in worktree t-5215): the original diagnosis was wrong. frob.app.telemetry.redact_command's OWN body already correctly imports from frob.security._redact (T-1318's own fix, already in place) -- NOT from frob.gates._secrets. The actual leak is structural and much deeper: merely 'import frob' (the top-level package, before frob.app.telemetry is ever touched) already loads all 103 frob.gates.* modules. Traced with python -X importtime: frob/__init__.py imports frob.doctor -> frob.app.run_runner -> frob.policy._models -> frob.policy/__init__.py, which does 'from frob.gates._models import Severity, Violation, WaiverRef' at module level (src/frob/policy/__init__.py:34). Since frob.gates._models is a SUBMODULE of frob.gates, Python always executes frob/gates/__init__.py in full first (ordinary package-import semantics, the exact mechanism frob.security's own module docstring describes) -- so frob.policy's one import eagerly loads the entire gates stage roster, and frob.policy is reached from frob's own top-level __init__.py before ANY caller-chosen submodule (telemetry included) gets a chance to avoid it. This is out of this ticket's declared scope (src/frob/app/telemetry/__init__.py) -- the real fix touches src/frob/policy/__init__.py (and possibly frob/__init__.py's own frob.doctor import) and needs an architecture decision (move Severity/Violation/WaiverRef to a frob.gates-independent shared location the way T-1318 already did for the secret-scan primitives, vs. make frob.policy's import lazy/deferred, vs. accept this and change what this test actually asserts) rather than a blind mechanical fix under time pressure. Recommend re-scoping to src/frob/policy/__init__.py and treating this as its own architecture ticket.