---
id: T-4301
title: expose dev-version-bump toggle/ack via a CLI surface (frob release status)
state: in-progress
kind: feature
origin: human
created: '2026-09-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/release/_cli.py
- docs/modules/release.md
- tests/test_release.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/modules/release.md
  reason: 'T-4301: status verb''s own docs anchor and unit tests live in these shared
    files, not just src/frob/release/_cli.py'
  actor: logan
  at: '2026-09-08'
- op: add
  glob: tests/test_release.py
  reason: 'T-4301: status verb''s own docs anchor and unit tests live in these shared
    files, not just src/frob/release/_cli.py'
  actor: logan
  at: '2026-09-08'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Follow-up from T-4184: frob.release.dev_version_bump_enabled/dev_version_major_ack are public read-only introspection functions with no in-repo CLI caller yet (WIRE001, waived on both pending this ticket). Wire them into a real consumer -- e.g. a 'frob release status' subcommand printing whether the per-land dev-version bump is on and what major series is acknowledged -- so the public API this ticket added has an actual production caller, not just its own tests.