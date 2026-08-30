---
id: T-3446
title: strata export golden test_seccomp drifted from the committed golden
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
- tests/unit/strata/test_export_golden.py
- tests/golden/frob_export_seccomp.json
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

FAILING: tests/unit/strata/test_export_golden.py::TestExportGolden::test_seccomp
    golden JSON text differs from the current export.
The strata export for the seccomp fixture drifted from its committed golden (likely T-3260/T-3424 vmodel split adding an attrs field, or key ordering). Diff the two, decide whether the export or the golden is right, and if the golden must be regenerated do it via the documented regeneration path (check the test module docstring) and explain the delta in the Done report.
