---
id: T-3285
title: close-time disclosure check false-positives on split done-report.md
state: queued
kind: bug
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
- src/frob/tickets/_reporting.py
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
T-3196's close hit: 'Done report contains disclosure-shaped language (non-standard Done-report subsection (Changed))' even though the rendered/merged body (verified directly via _merge_sibling_done_report + disclosure_shaped_language in a REPL) returns None -- no disclosure. The live close path apparently reads a different body representation than the merge helper. Needs investigation: does close call disclosure_shaped_language on the pre-merge ticket.md body, or is there a double-splice duplicating the done-report.md content under ledger v2's split-file format?