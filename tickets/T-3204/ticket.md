---
id: T-3204
title: Budget-truncated frob check must report NOT_MEASURED, not a clean zero
state: queued
kind: bug
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/_check_chunking.py
- src/frob/app/check_runner.py
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
T-2391 follow-up (see its own Done report for the cut this splits from). frob check --budget N skips stage groups it cannot afford and today reports only a separate top-level budget JSON key (skipped_groups) -- it never marks any per-tool ToolResult as measurement=not_measured, and the overall exit code/human summary do not distinguish a budget-truncated run from a fully-measured clean one. Wire ToolResult.measurement (T-2391, src/frob/process/parsers/common.py) or a synthesized not_measured placeholder result for every stage _run_budgeted_check skips, and make CheckResult.unmeasured_results (src/frob/check/__init__.py) include them. Must-fire: a --budget run that truncates at least one stage group asserts that stage's ToolResult.measurement == not_measured. Must-stay-quiet: an unbudgeted run, or a budgeted run that completes every group, is unaffected.
