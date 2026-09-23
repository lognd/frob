---
id: T-draft-9fdc1fcd
title: 'Hook: deny self-matching pgrep -f pollers in Bash tool calls'
state: queued
kind: bug
origin: human
created: '2026-09-23'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .claude/hooks/pgrep-self-match-guard.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: .claude/hooks/pgrep-self-match-guard.py
  reason: hook script, shared shellscan helper, sync manifest, registration, guide
    section, test
  actor: logan
  at: '2026-09-23'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured 2026-09-23: 26 of about 40 live harness shells were poll loops that could never exit. 18 were `until ! pgrep -f "<literal>"` / `while pgrep -f "<literal>"` loops written by implementer agents: the literal pattern appears in the polling shell's own `bash -c` command line, so pgrep always matches the poller itself. Each stayed alive for hours (one for 21 h) after the watched command finished, and the agents' turns ended "waiting" on them.

Fix: a PreToolUse Bash hook (`.claude/hooks/pgrep-self-match-guard.py`) that denies a Bash command containing `pgrep -f <literal>` (or `ps ... | grep <literal>` without the `[f]oo` bracket trick) and names the recipes that do not self-match: `pgrep -x`, a pattern assembled from a variable, the bracket trick, or waiting on the harness task notification / a `$!` pid. One override: `FROB_SELF_MATCH_ACK=1`. Materialized to `~/.claude/hooks/` via the `MANAGED` list and registered in the project settings.
