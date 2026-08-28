---
id: T-3202
title: 'GATESTATUS001: meta-check for silently-regressed gate measurement status'
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
- src/frob/gates/_lexical_selfcheck.py
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
T-2391 follow-up (acceptance[3]): "a converted gate that returns a bare empty finding list without a status, when the meta-check runs, then it is reported, proving the doctrine is enforced structurally rather than by convention." T-2391's shipped slice (see its Done report) added ToolResult.measurement as a computed field derived from existing UNRESOLVED-severity data, but added no structural gate-on-gates enforcing that every gate family which CAN determine it measured nothing actually does so via that mechanism, mirroring LEXCHECK001 (src/frob/gates/_lexical_selfcheck.py) and PORT001 (T-2384) as the ticket's own named precedents. Design a GATESTATUS001 meta-check: scan gate modules for one that constructs Severity.UNRESOLVED violations in some branches (proving it recognizes an unmeasurable case) but returns a genuinely empty violation list on some OTHER unresolvable input path without emitting anything -- the silent-regression shape. This is nontrivial static analysis (distinguishing "legitimately found nothing" from "silently gave up") and needs its own design pass before implementation; do not implement by pattern-matching source text alone (T-1662's own lexical-decision-is-itself-a-defect standard applies here too).
