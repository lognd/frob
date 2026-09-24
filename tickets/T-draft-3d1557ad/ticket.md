---
id: T-draft-3d1557ad
title: LAYOUT review gate
state: queued
kind: feature
origin: human
created: '2026-09-24'
priority: medium
parent: null
tier: story
sprint: layout-gate
runs_last: false
milestone: v0.537.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
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
frob-side LAYOUT review gate over crunk's gallery manifest: vendor the manifest schema, register crunk as a REQUIRED_FOR_FAMILY tool, add LAYOUT001-00x rules (render-exists, review-current by source_hash, unreviewed=fail), and bind the review verdict as ticket evidence plus a strata verification node. F-3 (A11Y/SEO/WEBPERF over the rendered catalog) is deferred to a follow-on epic per owner decision Q4 and is not filed here.

Owner decisions (2026-09-24): verdict expires on any byte change of component source or fixture props (manifest source_hash); screenshots are CI artifacts, manifest JSON is the only committed artifact.

Cross-repo dependency: blocked on the crunk repo leaf titled 'Define versioned gallery manifest JSON schema' (crunk epic 'gallery: every component and layout rendered and reviewed en masse'). Ids differ across repos, so the edge is recorded here by title.

Tree: /tmp/claude-1000/-home-logan-projects-frob/f95beb8e-97d5-4dd4-9038-3ffab8a3a4ea/scratchpad/CRUNK-GALLERY-TREE.md (sections 2 and 5; section 5 overrides).
