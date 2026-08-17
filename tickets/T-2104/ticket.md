---
id: T-2104
title: A stale blocked_by does not self-heal when its blocker narrows scope
state: done
kind: bug
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_doable.py
- tests/test_tickets.py
evidence_scope:
- tests/test_tickets.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_tickets.py
  reason: BUG002 evidence for T-2104 lives in this test file
  actor: logan
  at: '2026-08-17'
evidence:
- tests/test_tickets.py::TestDoableStaleBlockedBySelfHeals::test_narrowed_in_progress_blocker_self_heals
- tests/test_tickets.py::TestDoableStaleBlockedBySelfHeals::test_still_overlapping_in_progress_blocker_still_blocks
- tests/test_tickets.py::TestDoableStaleBlockedBySelfHeals::test_queued_blocker_never_self_heals_on_scope
designated_repro_test: tests/test_tickets.py::TestDoableStaleBlockedBySelfHeals::test_narrowed_in_progress_blocker_self_heals
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 353475ea0beca8b5133f3c74601faad0e9b73516
---
T-2095 fixed scope narrowing propagation to the cross-worktree lease
side-channel's collision CHECK (a candidate no longer refused over a
path the holder has already released). It deliberately did NOT touch a
separate, related gap the same ticket's body called out explicitly: a
stale `blocked_by` record does not self-heal when its blocker narrows.

T-2076's block against T-1669 survived T-1669's own narrowing and had to
be cleared through the store API by hand, because no unblock verb exists
-- `frob ticket block <id> --by <holder>` records a `blocked_by` entry
once, at refusal time, and nothing re-checks it later against the
holder's current (possibly since-narrowed) live lease.

Needs a verb (or an automatic reconciliation pass, e.g. folded into
`doable`/`sweep`) that re-evaluates an existing `blocked_by` entry against
its blocker's CURRENT live lease scope (the same side-channel T-2095's fix
now consults) and clears the block once the overlap that caused it is
gone -- mirroring T-2095's own monotone-narrowing-is-safe reasoning: a
`blocked_by` entry may only ever be CLEARED by this mechanism, never
newly created.

Out of scope for T-2095 itself (declared scope src/frob/tickets/_scope.py
only) -- this needs the blocked_by mutation/reconciliation surface
(likely src/frob/tickets/_doable.py or a lifecycle command), not the
scope-lease-conflict predicate T-2095 touched.