---
id: T-4609
title: fast pre-flight ty-check-only step before dispatching a full frob ticket land
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: medium
parent: null
tier: ticket
sprint: v0.535.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.535.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-4581 why-file finding: T-3233's FIRST land attempt (06:49:36-06:50:18, LAND-EXIT=1) was refused at +2.9s by 'ty check found 1 NEW error' in the ticket's own touched file (a real regression, tests/unit/test_cli_lang_choices_drift.py against src/frob/_cli_parsers/_core.py's LANG_CHOICES drift, since fixed in d164d5df8). The retry did not happen until 08:32:28 -- a ~1h42m gap outside land's own runtime, but the failed dispatch itself still cost a full land-queue slot (T-1693/land-throughput: 15 lands in 10.5h overnight) for a check ('ty check' over the touched files alone) that would have caught this in seconds, before ever invoking the heavier 'frob ticket land' pipeline. Propose a lightweight pre-flight ('frob ticket land --dry-run' or a documented finisher-agent step) that runs just ty+ruff over the ticket's own touched files before the real land dispatch, so this exact failure shape is caught pre-dispatch instead of consuming a land slot.
