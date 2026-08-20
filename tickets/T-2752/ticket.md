---
id: T-2752
title: document T-2740's waiver-liveness classifier (WaiverLiveness/classify_waiver_liveness/render001_scans)
  in docs/modules/app.md and docs/modules/render.md
state: queued
kind: docs
origin: human
created: '2026-08-20'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/modules/app.md
- docs/modules/render.md
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
T-2740 added WaiverLiveness/classify_waiver_liveness (frob.app.ticket_runner._waive_audit) and render001_scans (frob.gates._render_lint), both already pointing frob:doc at existing anchors (docs/modules/app.md#waive-audit-t-2467, docs/modules/render.md#renderer) via AFFECT001 waivers -- docs/modules/app.md was held under T-2694's live cross-worktree lease for T-2740's entire duration, so the anchor prose itself could not be extended in that diff. Add a short paragraph to each anchor describing the new --check-liveness scan flag and the necessary/inert/unverified classification it reports.