---
id: T-3220
title: frob clean --deep wholesale-deletes .frob/, which now also deletes rapid-debt.jsonl
  (T-2997)
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
- src/frob/clean/_rules.py
- src/frob/clean/_core.py
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
T-2997 moved rapid-debt.jsonl's write target from the tracked repo root to .frob/rapid-debt.jsonl (gitignored). frob clean --deep (tier 3, src/frob/clean/_rules.py _TIER3_PATTERNS) shutil.rmtrees the ENTIRE .frob/ directory, which now includes this debt ledger -- a real data-loss mode T-2997's own acceptance bar ('do not silently discard it') explicitly warns against, discovered while verifying T-2997's 'confirm nothing depends on reading it' requirement rather than assumed. Decide and implement a fix: either carve rapid-debt.jsonl out of the tier-3 walk (an explicit exclude pattern), or move its write target outside .frob/'s clean --deep blast radius, or get an explicit owner sign-off that clean --deep may destroy this telemetry too (matching the T-2997 tradeoff already accepted for clone-survival).