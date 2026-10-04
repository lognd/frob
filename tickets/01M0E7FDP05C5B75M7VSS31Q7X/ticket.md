+++
id = "01M0E7FDP05C5B75M7VSS31Q7X"
title = "document T-2740's waiver-liveness classifier (WaiverLiveness/classify_waiver_liveness/render001_scans) in docs/modules/app.md and docs/modules/render.md"
type = "docs"
category = "done"
outcome = "wont-fix"
priority = "medium"
reporter = "human"
created = "2026-08-20T00:00:00Z"
updated = "2026-10-04T21:07:23Z"
aliases = ["T-2752"]
labels = ["milestone:1.0.0", "v1-cluster:F1"]
scope = ["docs/modules/app.md", "docs/modules/render.md"]
+++

T-2740 added WaiverLiveness/classify_waiver_liveness (frob.app.ticket_runner._waive_audit) and render001_scans (frob.gates._render_lint), both already pointing frob:doc at existing anchors (docs/modules/app.md#waive-audit-t-2467, docs/modules/render.md#renderer) via AFFECT001 waivers -- docs/modules/app.md was held under T-2694's live cross-worktree lease for T-2740's entire duration, so the anchor prose itself could not be extended in that diff. Add a short paragraph to each anchor describing the new --check-liveness scan flag and the necessary/inert/unverified classification it reports.
