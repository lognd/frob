---
id: T-4686
title: Orphaned check child after its sweep parent dies
state: queued
kind: bug
origin: human
created: '2026-09-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.535.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_rapid_sweep.py
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
Found while working T-4660 (post-publish sweep lock window). MEASURED (2026-09-19 15:45): a sweep-async worker died while its own nested frob check --json child was still running; the check child was reparented to init and kept running, orphaned, still holding a derived_state_lock SHARED hold that the next land's EXCLUSIVE acquire waited on.

Closing this needs the check child to die when its sweep-worker parent dies (e.g. a SIGTERM/SIGINT handler on the worker that kills its own process group, or PR_SET_PDEATHSIG on the spawned child). Attempted during T-4660: adding this introduces a genuinely new process-control capability on src/frob/app/ticket_runner/_rapid_sweep.py (SYS100 node=cli), which requires a design/frob.strata may process-control via entry -- design/frob.strata was leased by another in-progress ticket (T-4112) at the time, and frob ticket scope --add was refused with ScopeLeaseConflict. T-4660 shipped only the lock-window fix (its own primary, ticket-listed acceptance criteria) and left this second incident to this follow-up so it could land clean.

Positive control: a test that starts a fake sweep worker, spawns a long-running child under it (no start_new_session), sends SIGTERM/SIGKILL to the worker, and asserts the child exits within a bounded time -- currently fails on dev (the child survives, reparented to init).