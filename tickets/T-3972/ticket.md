---
id: T-3972
title: 'LOOP001: asyncio.run inside a loop'
state: queued
kind: security
origin: agent
created: '2026-09-06'
priority: medium
parent: T-3919
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/perf/_hotpath_smells.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given asyncio.run(...) called inside a for/while loop body, when frob check
    runs, then LOOP001 fires
  evidence: []
- text: given a recurring-job component matching this shape with only a single-cycle
    test, when frob check runs, then a two-cycle test obligation is reported
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-3919 item 9. FINDING THIS WOULD HAVE CAUGHT: asyncio.run(...) called inside a loop, capturing outer/loop-scoped state on each iteration -- each call spins up a fresh event loop, so any state meant to persist or accumulate across iterations (a connection, a semaphore, an in-flight task set) silently resets or leaks. Their docstring claim "no loop is ever nested" was itself one of the FALSE claims in the backend audit (see the docstring-derived-invariants convergence ticket), so this needs its own structural detector independent of docstring text.

Proposed rule LOOP001: a lexical/AST shape flagging asyncio.run(...) (or equivalent event-loop-entry calls) inside a for/while loop body. Pair with a scheduler test obligation: a component using this pattern for a recurring job needs a test that runs it for at least two cycles (to surface the loop-scoped-state-reset bug a single-cycle test cannot see).
