---
id: T-0152
title: packaging is an undeclared runtime dependency -- bare frob install crashes
  on import
state: done
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- pyproject.toml
- uv.lock
- tests/unit/test_runtime_deps.py
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_runtime_deps.py::TestRuntimeDepsDeclared::test_every_unguarded_third_party_import_is_declared
- tests/unit/test_runtime_deps.py::TestRuntimeDepsDeclared::test_packaging_regression_is_locked
designated_repro_test: null
threat: null
component: null
---
T-0147's src/frob/vet/_cve.py imports packaging.version at module level, but packaging was only in the dev dependency group -- a bare wheel install (uv tool install / pip install) crashed every frob invocation with ModuleNotFoundError: No module named 'packaging', found when reinstalling the global tool after T-0150 landed. Same defect class as T-0142. Fix: declare packaging>=24 in [project].dependencies; add a drift test asserting every top-level third-party import under src/frob/ resolves to a declared [project] dependency so the next undeclared import fails in CI instead of at install time. Coordinator hotfix: toolchain-blocking, fixed inline with ticket accounting rather than dispatched.