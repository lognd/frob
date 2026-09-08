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
Follow-up from T-4184: frob.release.dev_version_bump_enabled/dev_version_major_ack are public read-only introspection functions with no in-repo CLI caller yet (WIRE001, waived on both pending this ticket). Wire them into a real consumer -- e.g. a 'frob release status' subcommand printing whether the per-land dev-version bump is on and what major series is acknowledged -- so the public API this ticket added has an actual production caller, not just its own tests.