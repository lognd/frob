---
id: T-3739
title: re-stamp stale frob-deprecated-baseline.lock.json (DEPR006 abandoned-producer)
state: queued
kind: bug
origin: human
created: '2026-09-03'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- frob-deprecated-baseline.lock.json
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
frob check reports DEPR006: the deprecated-baseline lock producer looks ABANDONED -- 1389 commits touched src/frob/**/*.py since frob-deprecated-baseline.lock.json was last stamped (2026-07-28), with no re-stamp and no pin. Found while working T-3737 (flaky-test marker mission, scope tests/**+pyproject.toml only, cannot touch this lock file). Re-run tighten_deprecated_baseline and commit the refreshed lock, or add a top-level pin with reason+ticket if this is a deliberate freeze.