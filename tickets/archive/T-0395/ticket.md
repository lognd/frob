---
id: T-0395
title: 'advisories: large-file residue after calibrated thresholds (T-0373)'
state: done
kind: feature
origin: human
created: '2026-07-20'
priority: medium
blocked_by:
- T-0373
- T-1072
- T-1076
- T-1074
parent: T-0376
tier: ticket
sprint: null
scope:
- src/frob/
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
threat: null
component: null
---
After T-0373 re-thresholds frob-arch large-file to 800 lines / 60 (function), address the residue that still exceeds 800 lines among the 34 large-file advisories: real module splits, or accepted-with-reason for files that don't decompose cleanly. Acceptance: frob check arch large-file advisories at the calibrated threshold reduced to zero unresolved.

## Failure log
- 2026-07-28 attempt 1: 31 in-scope large-file findings after T-0373 calibration (43 total minus 12 strata/vet sibling-owned), up to 12047 lines (gates/__init__.py); large-file is unwaivable per docs/modules/gates.md, real splits needed -- too large for one pass, decomposition tickets filed