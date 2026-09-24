---
id: T-draft-887a320c
title: Register crunk as REQUIRED_FOR_FAMILY tool for LAYOUT
state: queued
kind: feature
origin: human
created: '2026-09-24'
priority: medium
blocked_by:
- T-draft-a03f18af
parent: T-5747
tier: ticket
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
scope:
- src/frob/doctor.py
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
Register crunk as a REQUIRED_FOR_FAMILY tool for the LAYOUT family: _FAMILY_TOOL_RELEVANCE entry plus relevance predicate in doctor.py (no never-fail override, per T-5335).

Positive control: on a fixture repo with gallery org buckets declared but no crunk binary on PATH, scan_external_tools returns a FAILING finding; removing the buckets makes it silent.

Doc page: docs/modules/doctor.md#required-for-family

Cross-repo dependency: blocked on the crunk repo leaf titled 'Define versioned gallery manifest JSON schema' (crunk epic 'gallery: every component and layout rendered and reviewed en masse'). Ids differ across repos, so the edge is recorded here by title.

Tree: /tmp/claude-1000/-home-logan-projects-frob/f95beb8e-97d5-4dd4-9038-3ffab8a3a4ea/scratchpad/CRUNK-GALLERY-TREE.md (sections 2 and 5; section 5 overrides).
