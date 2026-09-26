---
id: T-draft-4acdecec
title: frob serve daemon warns every tick when the root is not a git repo instead
  of disabling once or resolving the nearest repo
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
- src/frob/serve/_daemon.py
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
Reported by the project-hullbreach session (2026-09-26): with the MCP stdio
entry `frob serve` started from /home/logan/projects/project-hullbreach,
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
