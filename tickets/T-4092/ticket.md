---
id: T-4092
title: 'H3-3: units/epoch obligation on time-typed ABI parameters'
state: queued
kind: invariant
origin: agent
created: '2026-09-06'
priority: medium
parent: T-4089
tier: story
sprint: null
runs_last: false
milestone: 1.1.0
flavour: quality_objective
due: null
rank: null
points: null
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
scope:
- src/frob/gates/_inv.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.538.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
- field: sprint
  old_value: v0.538.0
  new_value: v1.1.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
- field: tier
  old_value: ticket
  new_value: story
  reason: 'E2 (T-5766, owner decision Q3): reclassify kind:invariant as tier=story;
    evidence-split into a child ticket + kind:invariant retirement deferred to a follow-up
    leaf'
  actor: logan
  at: '2026-09-25'
- field: flavour
  old_value: null
  new_value: quality_objective
  reason: 'E2 (T-5766, owner decision Q3): reclassify kind:invariant as flavour=quality_objective;
    evidence-split into a child ticket + kind:invariant retirement deferred to a follow-up
    leaf'
  actor: logan
  at: '2026-09-25'
designated_repro_test: null
acceptance:
- text: given a design note settling the frob:invariant form for naming an ABI parameter's
    epoch/units explicitly, when this ticket's design step completes, then the note
    is attached before implementation
  evidence: []
- text: given a time-typed ABI parameter with no bound epoch invariant, when the check
    runs, then it is flagged as underspecified
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
H3-3 (F-296). Same structural theme as H3-1a (this epic): a prose contract enforced on one side of an ABI boundary and unenforced/ambiguous on the other. Here BOTH implementations are internally consistent and match each other exactly -- a parity gate (like H3-1a's) is the WRONG instrument for this one; the gap is purely in what the shared prose contract fails to say.

VERIFIED: git grep for a units/epoch obligation construct over a time-typed parameter found nothing in src/frob.

FINDING THIS WOULD HAVE CAUGHT: COMP-1703/COMP-1712 both say a value is "time-decaying" WITHOUT NAMING THE EPOCH (what zero means -- seconds since process start, since the originating pointer event, since the Unix epoch, etc.), so the caller was free to pass a different clock than the callee assumed. Both sides implement the SAME wrong assumption consistently, so no diff/parity check would ever catch it -- the defect is that the CONTRACT itself is underspecified in prose, not that the two implementations disagree.

Proposed: a units/epoch obligation on a time-typed ABI parameter -- a frob:invariant naming the parameter's epoch explicitly (their worked example: "hotspot_bands' time is seconds since the originating pointer event") bound to a test that passes a large page-clock value (a value that would only make sense under a wrong-epoch assumption) and asserts the expected behavior (their example: the ripple effect is still present) still holds. This generalizes beyond time: any ABI parameter whose UNITS or REFERENCE FRAME are stated in prose only (a distance in what unit, an angle in degrees vs radians) is the same underspecified-contract shape -- scope this ticket to the time/epoch case specifically as the first instance, and note the generalization as a possible follow-up rather than building it now.
