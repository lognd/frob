---
id: T-draft-31c35523
title: 'audit the 40 open epics: outcome-check or dropped child per epic'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
blocked_by:
- T-5776
parent: T-5748
tier: ticket
sprint: null
runs_last: false
milestone: v0.536.0
flavour: null
due: null
rank: null
points: 8
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: parent
  old_value: null
  new_value: T-5748
  reason: part of the ledger-tiers story (T-5748), the E3 scope cut
  actor: logan
  at: '2026-09-25'
- field: points
  old_value: null
  new_value: '8'
  reason: ticket sizing
  actor: logan
  at: '2026-09-25'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
found while working E3 (T-5776, ledger-tiers): closed the all-children-done epics (T-3611, T-4513) but per owner decision every remaining open epic needs a real frob:outcome-invariant/frob:outcome-metric field or a dropped child recording why it is stalled (TIER003's own requirement). The TIER003 epic-outcome WARN rule (B3, T-5780, _tier003_epic_closer) is the mechanical guard that keeps this debt visible in frob check until this audit lands -- it already flags every DONE-but-unaudited epic and will flag these once they reach done, so nothing regresses silently while this leaf is outstanding.

Live count at filing time (drifted from the tree's 40 baseline -- 39/40 was a snapshot, not a contract, same as E1/E2's own drift note): 41 open epics need auditing, grouped by whether any direct child is still in-progress (2) vs all children queued or none (39).

IN-PROGRESS group (2): T-3004, T-4410

QUEUED-ONLY group (39): T-0969, T-1273, T-1382, T-1597, T-1609, T-1686, T-2202, T-2964, T-2982, T-2994, T-3022, T-3203, T-3231, T-3505, T-3542, T-3919, T-3920, T-3927, T-3928, T-3942, T-3984, T-4025, T-4036, T-4050, T-4071, T-4084, T-4089, T-4109, T-4135, T-4157, T-4166, T-4175, T-4182, T-4272, T-4651, T-4662, T-5140, T-5149, T-draft-5b96fa72