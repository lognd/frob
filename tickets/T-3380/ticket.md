---
id: T-3380
title: ruff format repo-wide sweep (81 files, no owning gate)
state: queued
kind: bug
origin: human
created: '2026-08-29'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- '**/*.py'
scope_breadth_ack: true
scope_breadth_ack_reason: 'a repo-wide ruff format --check failure has no natural
  narrower scope -- gate:FMT only scans diff-touched frob: directive lines per its
  own scope-note and never catches this; the sweep itself is purely mechanical (ruff
  format .)'
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
ruff format --check . measured 81 files needing reformatting on current main. gate:FMT (FMT001) only scans frob: directive-comment lines touched by the current diff -- it never scans the whole tree -- so this drift was invisible to frob check and accumulated unowned. Fix: run ruff format . and land the 81-file diff as one standalone sweep, on its own commit, nothing batched with it. frob fmt --check (the repo's own directive-line formatter) separately flags 5 Rust files (frob-core/src/*.rs, strata-core/src/**/*.rs) -- disjoint from ruff format's 81 Python files, confirmed zero overlap, so the two tools cannot fight each other on this sweep.