+++
id = "01M3DG64DB0MJWAP3FSY0YKP2N"
title = 'frob serve prints "--- Logging error --- I/O operation on closed file" on stdin EOF because a handler writes after the stream closes'
type = "bug"
category = "done"
outcome = "wont-fix"
priority = "medium"
reporter = "agent"
created = "2026-09-26T00:00:00Z"
updated = "2026-10-04T21:08:35Z"
aliases = ["T-6571"]
labels = ["milestone:0.535.0", "v1-cluster:E1"]
scope = ["src/frob/serve/server.py", "src/frob/logging/"]
+++

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
