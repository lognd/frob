---
id: T-3967
title: 'RESULT001: network-I/O async def may not return None'
state: queued
kind: security
origin: agent
created: '2026-09-06'
priority: medium
parent: T-3942
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/arch/_abstraction.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given an async def performing recognizable network I/O with a bare return
    None on a failure path, when frob check runs, then RESULT001 fires
  evidence: []
- text: given the same function returning a typani Result or raising instead, when
    frob check runs, then the rule stays quiet
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
F-183 (T-3942 item 9). FINDING THIS WOULD HAVE CAUGHT: an async def performing network I/O (notify_admin_alert) returning None on failure, which let a caller mark alerts digested after a FAILED send. The consumer notes it violates this repo's own stated typani rule (fallible operations return Result[T, E], never a bare None/exception) that no gate currently enforces -- an intent-in-prose instance: CLAUDE.md/typani.md state the rule, nothing checks it.

Proposed rule RESULT001: an async def whose body performs recognizable network I/O (aiohttp/httpx/requests-async call, a socket send, an SMTP/webhook call) may not return None as its success/failure signal -- it must return a typani Result (or raise, if the codebase's convention is exceptions for this class). Verify scope: this is a Python-idiom rule most naturally paired with wherever the repo's own typani-adjacent lint/idiom rules already live (e.g. frob's own arch/idiom gates), not a new taint/callgraph subsystem.
