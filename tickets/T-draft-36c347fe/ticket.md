---
id: T-draft-36c347fe
title: 'frob-suggest: dedupe dual hook registration and make attempt counter per-agent-session'
state: queued
kind: bug
origin: human
created: '2026-09-19'
priority: high
parent: T-draft-8c7e665d
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .claude/hooks/*
- .claude/settings.json
- tests/test_hook_frob_suggest.py
- tests/test_hook_sync_claude_config.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: sync-claude-config.py does not materialize a second registration of a hook
    the project settings.json already registers for the same repo, deduped by hook
    basename+event
  evidence: []
- text: attempt counter is keyed per FROB_AGENT/session id (falling back to parent
    pid), not per command-shape machine-global
  evidence: []
- text: a single Bash call increments the attempt count exactly once, proven by a
    test
  evidence: []
- text: O_EXCL denial dedupe is preserved
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Leaf 1 of T-draft-8c7e665d. See scratchpad/HOOK-AUDIT.md section 0b.