---
id: T-6546
title: uv tool reinstall takes frob off PATH for ~1 minute; provide an atomic swap
  or a waiting shim
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
- src/frob/app/release_runner.py
- scripts/install_tool.sh
- docs/guides/install.md
- tests/unit/test_install_tool_atomic.py
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
Source: logand.app-v2 FROBLEMS.md (peer coordinator report, 2026-09-26). Reproduction lives in that repo (read-only for frob agents); the frob-side positive control must be a fixture here.

F-402: `uv tool install --force --reinstall` removes the `frob` executable from PATH for about a minute while the new environment builds; agents mid-command in consumer repos fail with 'command not found'. Deliver: a `frob self-install` (or scripts/install_tool.sh) that builds the new tool environment beside the old one and swaps the executable atomically (rename), or a shim on PATH that waits for the environment to exist; docs/guides/install.md documents the safe refresh; positive control: a test that runs the install path while a `frob --version` loop runs in parallel and asserts zero failures.
