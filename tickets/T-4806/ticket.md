---
id: T-4806
title: 'ci: bump pinned GitHub Actions from Dependabot PRs 6-10 on dev in one commit
  and retarget Dependabot to dev'
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .github/workflows/*.yml
- .github/dependabot.yml
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
Apply the five open Dependabot PRs (6-10, targeting frozen main) as one commit on dev: bump actions/checkout 4.4.0->7.0.1, actions/cache 4.3.0->6.1.0, actions/upload-artifact 4.6.2->7.0.1, actions/download-artifact 4.3.0->8.0.1, astral-sh/setup-uv 5.4.2->10.0.1 (exact SHAs from each PR diff). Add target-branch: dev to dependabot.yml. Check release.yml for artifact v4->v7/v8 breaking changes and setup-uv v10 cache default changes; adjust minimally with comments. PRs are then closed as superseded by the coordinator (not by this ticket).