---
id: T-3904
title: port frob.serve.server to mcp 2.x API (FastMCP -> MCPServer)
state: queued
kind: feature
origin: human
created: '2026-09-05'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/serve/**
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
Triggered by T-3857's mcp<2 pin: frob[serve] is pinned below mcp 2.x to unblock the alpha rather than risk an unverified port. T-3857 checked mcp 2.1.1's MCPServer directly (downloaded wheel, not just the changelog): the constructor's name positional, the @server.tool() decorator, and server.run(transport="stdio") all exist with a compatible signature, so the port itself looks low-risk -- but nothing has run frob serve against a real mcp 2.x client end-to-end, which is why this is follow-up, not part of T-3857. Do the port, verify end-to-end against a real mcp 2.x install, then raise the pyproject.toml pins (serve extra + dev group) past <2. See docs/guides/release.md's Decision 5 section for the full T-3857 context.