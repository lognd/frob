---
id: T-5437
title: 'claude sync: keep user-level registrations for hooks materialized for global
  use'
state: queued
kind: bug
origin: human
created: '2026-09-23'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.535.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
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
`sync-claude-config.py` dedupes any `~/.claude/settings.json` hook registration whose (event, basename) is also registered by the project `.claude/settings.json` (HOOK-AUDIT 0b). That is correct inside this checkout, but it also strips the registrations that make a materialized hook active in OTHER repos: on 2026-09-23 a sync removed the user-level `frob-suggest.py` and `diagnosis-nudge.py` entries, and it strips the new `pgrep-self-match-guard.py` (T-5436) entry every run, so the owner's "sync to global" intent is undone by the tool that implements it, and `--check` reports the restored entry as DRIFT.

Fix: distinguish "materialized for global use" hooks from "project-only" ones in `MANAGED` (a third tuple field or a separate `GLOBAL_HOOKS` set), and have dedupe skip those. The double-fire inside this repo is then handled by the hook itself (an env guard such as `FROB_HOOK_RAN_<name>` set by the first invocation), not by deleting the user entry. `--check` must stop flagging a global entry for a hook in that set.
