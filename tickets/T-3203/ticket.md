---
id: T-3203
title: Full MEASURED/NOT_MEASURED/NOT_APPLICABLE migration across all frob check gates
state: queued
kind: bug
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: epic
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/modules/gates.md
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
T-2391 epic follow-up: the full MEASURED/NOT_MEASURED/NOT_APPLICABLE type migration across all ~52 frob check gates (frob.gates.*), per T-2391's own body: "a default-MEASURED shim keeps existing gates compiling while they are converted one at a time." T-2391's shipped slice (see its Done report) delivered the type substrate (ToolResult.measurement/measurement_reason, computed fields, backward-compatible default "measured") and wired it retroactively for every gate family already using T-1664's Severity.UNRESOLVED signal via _gates_family_result (all *_SCHEMA config-table validators, FLAGCOV001, REF001/REF002) -- that is a real subset, not a shim covering everything. Remaining gates that can determine "no declared surface" or "matcher never fired" (T-2391's instances 2 and 3: hardcoded layout, inert waivers from path-shape mismatch) still report bare empty lists with no measurement signal at all. This ticket tracks converting each remaining gate family one at a time to explicitly self-report NOT_MEASURED/NOT_APPLICABLE where it can determine that, rather than relying solely on the generic UNRESOLVED-severity inference. Parent/tracking ticket -- break into per-gate-family children as they are picked up.
