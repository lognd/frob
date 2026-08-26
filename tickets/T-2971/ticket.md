---
id: T-2971
title: Re-measure macOS CI after T-2943/T-2969 land
state: queued
kind: docs
origin: human
created: '2026-08-26'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- N/A
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
T-2969 audited all 12 candidate test_cli_*.py files for the T-2943
missing-git-init pattern and found none of them carry it (see T-2969's
Done report for the full per-file table). T-2969's acceptance item 2
asked for a real macOS CI run, post T-2943's land, to re-measure whether
the 156-failure macOS baseline shrank as expected and to check whether
any of the 12 candidate files still fail there specifically as a genuine
macOS-only remainder. That requires triggering/observing an actual macOS
CI run, which a worktree agent cannot do. File this as a coordinator-only
follow-up: trigger a macOS CI run on current main and compare the new
failure count/composition against the pre-T-2943 156-failure baseline.
