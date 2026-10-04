+++
id = "01M3DG64DGC9JDQWGY6HY0EQY8"
title = "frob serve daemon warns every tick when the root is not a git repo instead of disabling once or resolving the nearest repo"
type = "bug"
category = "triage"
priority = "medium"
reporter = "agent"
created = "2026-09-26T00:00:00Z"
updated = "2026-09-26T00:00:00Z"
aliases = ["T-6576"]
labels = ["milestone:0.535.0", "v1-cluster:E1"]
scope = ["src/frob/serve/_daemon.py"]
+++

Reported by the project-hullbreach session (2026-09-26): with the MCP stdio
entry `frob serve` started from ~/projects/project-hullbreach,
which is not a git repo (its children game/ and platform/ are), the daemon
loop logs "WARNING: serve: daemon: could not resolve main HEAD under
<root>" on every tick. Verified on dev b41443f46d: `_main_head` in
src/frob/serve/_daemon.py warns on each call and both pollers call it per
tick.

Deliver (automatic tier): resolve the state once at daemon start; when the
root is not a git repo, log one line that post-land/rebase polling is
disabled for that root and skip the pollers until the root changes; when
child directories are git repos, say so in that one line. Positive
control: a fixture root with no .git and two ticks; exactly one warning.
