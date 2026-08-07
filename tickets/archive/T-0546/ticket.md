---
id: T-0546
title: 'check: unmapped/unknown project type silently falls back to the Python pipeline
  (T-0404 finding 6)'
state: done
kind: bug
origin: auditor
created: '2026-07-21'
priority: medium
parent: T-0404
tier: ticket
sprint: null
scope:
- src/frob/app/check_runner.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
threat: null
component: null
---
docs/audits/lang-check-docs.md finding 6. _run_auto_detected_stages: detected = _detected_types(root) or [detect_project_type(root)]; _dispatch_check maps any unrecognized type (incl. unknown) to _dispatch_check_python. A repo with no sentinel files runs the full Python gate stack over a non-Python tree (ruff/ty noise) rather than a clear unsupported-project-type failure. Fix direction: make unknown/unmapped types a loud config error, not a silent Python fallback.