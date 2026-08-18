---
id: T-2467
title: 'Reshape T-1614: periodic watermark-based waiver audit, drop runs_last'
state: queued
kind: security
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/**
- src/frob/app/**
- tickets/T-1614/**
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
T-1614 is currently `runs_last`: undispatchable via `frob ticket start`
while any other ticket is queued/in-progress. This repo files new
tickets faster than it drains them on most days (measured: 48 open
tickets at time of filing, continuous inflow) -- so "after all other
work is complete" is a condition that structurally will not hold. This
is not a deferred ticket; it is an unreachable one, and it has sat as
rot-flagged for 13+ days with nobody able to legally start it.

The audit's INTENT is sound (a waiver's honesty can only be judged
against finished code, and judging early condemns honest waivers whose
follow-up has not landed yet) -- the ONE-SHOT TERMINAL SHAPE is what is
wrong, not the goal.

Reshape T-1614 (and retire its `runs_last` flag) into a periodic,
watermark-based audit instead:

1. Add a persisted watermark (e.g. a commit sha or timestamp in
   `.frob/waive-audit-watermark.json`, mirroring the shape of existing
   `.frob/*.json` state files such as baseline-chunks/coverage-stamp)
   recording the last point a full waiver audit completed.
2. A new ticket-filing or gate mechanism scans `frob:waive` directives
   ADDED (via git blame/log, not full-repo re-scan) since the
   watermark, and either (a) opens a narrowly-scoped audit ticket over
   just that incremental set when the count crosses a threshold, or
   (b) folds into a standing gate stage the coordinator runs
   periodically (same operational shape as the existing WAIVE004
   dead-waiver sweep referenced in T-1614's own body).
3. On completion of an audit pass, the watermark advances to the
   current tip -- so the NEXT audit is scoped to what changed since,
   never the whole repo, and never blocked on repo-wide queue-empty.
4. T-1614's own classification rubric (STILL NECESSARY AND HONEST /
   OBSOLETE / COP-OUT / PERMANENT BY DESIGN) carries over unchanged --
   only the triggering/scoping mechanism changes.
5. Drop T-1614's `runs_last` flag once this lands; replace it with
   this periodic mechanism as the ticket's operating mode.

Do not lose the original T-1614 prose (classification rubric, the
specific patterns this drive already learned to look for -- reason-
restates-rule, orphaned follow_up, bulk-waiver clustering, structurally-
unfireable-rule noise) -- fold it into the new periodic ticket's body
rather than discarding it.

This does not retroactively bless every waiver added before the
watermark exists -- the FIRST run of the new mechanism should audit
the full existing set once (a bounded, one-time catch-up pass), then
every subsequent run is incremental.
