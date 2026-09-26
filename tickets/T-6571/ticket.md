---
id: T-6571
title: frob serve prints "--- Logging error --- I/O operation on closed file" on stdin
  EOF because a handler writes after the stream closes
state: queued
kind: bug
origin: agent
created: '2026-09-26'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.535.0
flavour: null
due: null
rank: null
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
- src/frob/serve/server.py
- src/frob/logging/
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
Reported by the project-hullbreach session (2026-09-26): when the MCP
client closes stdin, `frob serve` prints "--- Logging error ---
ValueError: I/O operation on closed file" during shutdown: a log handler
writes to the already-closed stream. Reproduce: `printf '' | frob serve`
from any repo and read stderr.

Deliver: on stdin EOF, flush and detach the stream handler (or route
shutdown logging to the file handler only) before the stream is closed;
serve exits 0 with no logging-error banner. Positive control: a subprocess
test that pipes an empty stdin into `frob serve` and asserts stderr has no
"Logging error".

Context for the same report: the MCP client's startup connection failed
once while `frob --version` was 0.531.1.dev338; a manual initialize over
stdio afterwards answered (serverInfo frob 1.30.0, 10 tools). The likely
cause is the global `uv tool install --reinstall` swap that blanks frob on
PATH for a few seconds (fleet-health note); no fix here beyond the two
defects above.
