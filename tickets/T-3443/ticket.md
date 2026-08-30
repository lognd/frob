---
id: T-3443
title: frob-exports reports missing public symbols in frob.doctor and frob.lang._support
state: queued
kind: bug
origin: agent
created: '2026-08-29'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/doctor/__init__.py
- src/frob/lang/__init__.py
- src/frob/lang/_support.py
- tests/unit/test_exports.py
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
MEASURED on GitHub Actions run 33282540898 (ubuntu-latest, HEAD b94cea5d0, 2026-08-30) -- the first run that completed to 100% (20 failures of 12689). This failure is in the cross-platform set (fails on macOS too unless noted). Reproduce locally by node id with -p no:xdist first; if it passes locally, the defect is an environment dependency (git identity, tmp path shape, missing tool, timing) and the fix must make the test hermetic, not skip it.

FAILING: tests/unit/test_exports.py::TestFrobExportsPolicyResidue::test_all_nine_packages_report_zero_missing_symbols
    frob-exports still reports missing symbols: {src/frob: [frob.doctor.scan_external_tools, frob.doctor.ToolCategory, frob.doctor.ExternalToolStatus], src/frob/lang: [lang._support.unfaceted_pack...]}
Public symbols added recently are not exported by their package __init__ per the exports policy. Run `uv run frob exports` to get the full offender list, add the exports (or __all__ entries) in the owning packages, and re-run the test.
