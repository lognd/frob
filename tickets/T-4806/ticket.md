---
id: T-4806
title: 'ci: bump pinned GitHub Actions from Dependabot PRs 6-10 on dev in one commit
  and retarget Dependabot to dev'
state: in-progress
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
body_changes:
- mode: append
  reason: record explicit acceptance criteria for evidence binding
  actor: logan
  at: '2026-09-19'
  old_length: 540
  new_length: 1101
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Apply the five open Dependabot PRs (6-10, targeting frozen main) as one commit on dev: bump actions/checkout 4.4.0->7.0.1, actions/cache 4.3.0->6.1.0, actions/upload-artifact 4.6.2->7.0.1, actions/download-artifact 4.3.0->8.0.1, astral-sh/setup-uv 5.4.2->10.0.1 (exact SHAs from each PR diff). Add target-branch: dev to dependabot.yml. Check release.yml for artifact v4->v7/v8 breaking changes and setup-uv v10 cache default changes; adjust minimally with comments. PRs are then closed as superseded by the coordinator (not by this ticket).

## Acceptance
1. All actions/checkout, actions/cache, actions/upload-artifact, actions/download-artifact and astral-sh/setup-uv `uses:` refs in .github/workflows/*.yml are 40-hex SHA pins with matching trailing version comments (bumped per Dependabot PRs 6-10).
2. .github/dependabot.yml declares target-branch: dev for the github-actions ecosystem.
3. release.yml's artifact-download steps using `pattern:` still pass merge-multiple: true and upload-artifact's retention-days input is preserved across the version bump (no silent breaking-change regression).