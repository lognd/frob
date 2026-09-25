---
id: T-draft-9f52cf73
title: 'land: refuse non-landable ticket state up front and auto-start a queued stacked
  leaf whose blockers are ahead in the queue'
state: queued
kind: bug
origin: agent
created: '2026-09-25'
priority: critical
parent: T-5630
tier: ticket
sprint: null
runs_last: false
milestone: 0.535.0
flavour: null
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
- src/frob/tickets/_land.py
- src/frob/tickets/_land_queue.py
- src/frob/tickets/_start.py
- tests/unit/tickets/test_land_state_precheck.py
- docs/modules/tickets-landing.md
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
Measured 2026-09-25 on the ledger-tiers stack (15 stacked leaves under
T-5748): a stacked successor cannot be `frob ticket start`ed while its
predecessor is still open (BlockerOpen) or holds an overlapping scope
lease (ScopeLeaseConflict), so the implementer built and enqueued the
leaves in state `queued`/`planned`. The land then merged them and failed
at the very end:

  ERROR: land: T-5765 close failed (InvalidTransition: State change not
  allowed by the state machine) after the merge already landed in the
  worktree (main untouched)

i.e. 15-30 minutes of land work per leaf thrown away for a state-machine
precondition the engine could have checked in the first second, and the
coordinator had to hold 13 queue entries and start each one by hand the
moment its predecessor lands.

Deliver (tiered safety):
1. Pre-check (automatic): `frob ticket land` refuses a ticket whose state
   cannot transition to done in the first pre-land step, naming the
   state and the verb that fixes it; the queue drain does the same at
   enqueue time (`--queue`), never at close time.
2. Automatic start at land (guaranteed safe when the ticket is queued,
   has a worktree binding, evidence and a done report, and every blocker
   is either done or AHEAD of it in the land queue): the land performs
   the queued -> in-progress transition itself and logs it, so a stacked
   series enqueued in dependency order with --allow-cross-ticket lands
   without a human between every leaf.
3. `frob ticket start --after <predecessor>` (real decision, explicit
   flag; the same flag T-draft-e388052a specifies for scope leases)
   accepts BlockerOpen when the named blocker is queued ahead in the land
   queue.
4. Positive control: base leaf + stacked leaf both enqueued; without the
   fix the stacked land fails at close; with it, the stacked leaf lands
   and is done, and a stacked leaf whose blocker is NOT in the queue is
   still refused up front.
