---
id: T-draft-d4509c7c
title: MCP tools frob_land_enqueue, frob_land_status, frob_land_queue over the socket
  daemon; agents enqueue through the tool
state: queued
kind: feature
origin: human
created: '2026-09-21'
priority: high
blocked_by:
- T-draft-796f317b
- T-draft-5ff600a1
parent: T-5106
tier: ticket
sprint: v0.535.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/serve/_tools.py
- src/frob/serve/_socketd.py
- docs/guides/agent-playbook.md
- tests/unit/serve/**
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
Leaf F of T-5106 (~2 pts). MCP surface for the queue. Blocked by leaf B (status shape) and leaf E (daemon owns the drain).
- `serve/_tools.py` gains `frob_land_enqueue(ticket_id, worktree)`, `frob_land_status(ticket_id)` and `frob_land_queue()` following the existing `Result[dict, ServeError]` tool shape, registered in `_socketd`'s name-keyed dispatch table; they call `enqueue`/`read_intent_record`/`queue_status` and never land inline.
- Agents call the tool instead of a shell land; the brief's "append to queue.txt" step is deleted from docs/guides/agent-playbook.md.
- Blocked also by T-3904 only if the mcp 2.x port changes the registration shape; otherwise independent.
- Positive control: an enqueue through the socket shows up in `--status` and lands via the daemon cycle.
