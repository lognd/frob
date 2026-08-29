---
id: T-3206
title: Add frob:doc anchor for ToolResult.measurement to process.md
state: done
kind: docs
origin: human
created: '2026-08-28'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/modules/process.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/test_process.py::TestToolResultMeasurement::test_measured_when_zero_diagnostics
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
docs/modules/process.md (frob.process.parsers.common's own doc home) was held by a LIVE cross-worktree lease (T-3191, in-progress) when T-2391 added ToolResult.measurement/measurement_reason and the Measurement type alias to src/frob/process/parsers/common.py. Add the frob:doc anchor for those three symbols to docs/modules/process.md#public-api once that lease clears (mirrors T-1999/T-2003's own precedent for the identical lease-collision shape in src/frob/tickets/_leases.py). Not silently dropped -- see the frob:waive COV001 directives T-2391 left on each symbol citing this ticket.