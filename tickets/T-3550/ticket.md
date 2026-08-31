---
id: T-3550
title: 'Design ledger-mirror batching (T-3544 successor): pending-queue + per-event
  sync commit, hazards enumerated'
state: queued
kind: feature
origin: human
created: '2026-08-31'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/design/ledger-mirror-batching.md
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
Successor to T-3544 (dropped after a measured attempt; parent epic T-3542).
Owner request stands: 109 of 300 recent main commits were per-verb
worktree-ledger mirror commits. Series AA's attempt established:
 - Batching mirrors requires a real design: a cross-process pending-mirror
   queue (under .frob/, keyed by ticket+verb, crash-safe) plus a flush
   that commits ONE "chore(tickets): sync ledger (T-a, T-b...)" per flush
   event (a land, a sweep completion, a bounded timer), reusing the T-3297
   merge driver so a flush never torn-merges against a live land splice.
   Per-verb commits stay ONLY where the commit is itself the fleet signal
   (block/unblock edges). Fleet liveness reads (leases, doable) must not
   regress -- enumerate which readers read the FILES (fine, flush-lagged)
   versus git history (must not matter).
 - The sweep-filing half of T-3544 was a wrong premise: sweeps file at
   most one ticket per run already. RE-MEASURE where the 41 file commits
   in 300 came from (coordinator batch filings? multiple sweep runs?) and
   state whether any batching applies there at all.
DELIVERABLE: the design (docs/design/ledger-mirror-batching.md) reviewed
against the live-fleet hazards above, THEN the implementation in a second
ticket you file, blocked by the design's owner sign-off if the design
finds a hazard needing an owner call. Do not implement in this ticket.
