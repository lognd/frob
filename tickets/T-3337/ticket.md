---
id: T-3337
title: frob release publish always bumps patch only, ignores REL001 required bump
  class
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
- src/frob/release/_publish.py
- scripts/bump_version.py
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
found while working T-3254 (docs/guides/release.md release-cut procedure).

MEASURED against this repo's live state (2026-08-28): frob release check says the change since the last stamp is MAJOR-class, requiring >= 0.531.0 from 0.530.0 (required_version's 0.x-series MINOR-position bump rule). frob release publish (== make upload) calls bump_patch_version / next_patch_version unconditionally (X.Y.Z -> X.Y.(Z+1)) and never consults diff_class/required_version at all -- it would compute 0.530.1, then stamp+sync+commit+push+build+publish that version, which does NOT satisfy the required >= 0.531.0 and fails this repo's own REL001 gate after already pushing and building.

WHAT TO BUILD: have _compute_plan (src/frob/release/_publish.py) call diff_class+required_version against the loaded manifest instead of unconditionally next_patch_version, so the computed bump always covers the observed public-API change class (NONE/PATCH/MINOR/MAJOR), matching what frob release check already reports. Keep --dry-run's side-effect-free contract. Update docs/commands/release.md's description ('Bumps the patch version...') to match once the behavior changes.

Until this closes, docs/guides/release.md documents doing the version bump by hand instead of via 'make upload' / 'frob release publish' at cut time.
