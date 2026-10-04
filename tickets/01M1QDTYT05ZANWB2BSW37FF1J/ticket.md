+++
id = "01M1QDTYT05ZANWB2BSW37FF1J"
title = "port frob.serve.server to mcp 2.x API (FastMCP -> MCPServer)"
type = "task"
category = "triage"
priority = "medium"
reporter = "human"
created = "2026-09-05T00:00:00Z"
updated = "2026-09-05T00:00:00Z"
aliases = ["T-3904"]
labels = ["milestone:1.0.0", "v1-cluster:E1"]
scope = ["src/frob/serve/**"]
+++

Triggered by T-3857's mcp<2 pin: frob[serve] is pinned below mcp 2.x to unblock the alpha rather than risk an unverified port. T-3857 checked mcp 2.1.1's MCPServer directly (downloaded wheel, not just the changelog): the constructor's name positional, the @server.tool() decorator, and server.run(transport="stdio") all exist with a compatible signature, so the port itself looks low-risk -- but nothing has run frob serve against a real mcp 2.x client end-to-end, which is why this is follow-up, not part of T-3857. Do the port, verify end-to-end against a real mcp 2.x install, then raise the pyproject.toml pins (serve extra + dev group) past <2. See docs/guides/release.md's Decision 5 section for the full T-3857 context.
