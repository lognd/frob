---
id: T-draft-65fc375e
title: Land's REL001 changelog regen sees stale manifest version, skips the real minor
  bump
state: queued
kind: bug
origin: human
created: '2026-09-19'
priority: medium
parent: T-4806
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: test_stale_worktree_manifest_still_lands_main_plus_one passes
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
CI run 35476139324 on dev: tests/ticket_land_suite/test_release.py TestRealCallbackStaleWorktreeManifest test_stale_worktree_manifest_still_lands_main_plus_one fails: after landing a ticket that adds a new public function (a real MINOR-class API addition) while the worktree's OWN .frob-release.json copy is stale (the T-1007 incident shape this test simulates directly), CHANGELOG.md's regenerated pending section still reads '## [0.183.0] - unreleased' (root's current, pre-bump manifest version) instead of the expected '## [0.184.0] - unreleased' (the real computed minor-bump target). Likely root cause in src/frob/app/ticket_runner/_land_cmd.py::_required_release_bump/_apply_release_bump_for_land: either diff_class(manifest, snapshot) is not seeing the new public symbol (graph snapshot built too early/from the wrong tree) so the bump computes as BumpClass.NONE and the changelog fragment/assemble step is skipped entirely, or _root_release_manifest is reading a stale manifest. Needs a git-state-timing investigation of when the graph snapshot and manifest are read relative to the squash-merge that lands the new symbol. NOTE: src/frob/app/ticket_runner/_land_cmd.py is currently leased by in-progress T-draft-f5ac9ec0 -- this ticket cannot start until that lease clears; block on it.