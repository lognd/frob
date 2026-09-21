---
id: T-5124
title: 'frob-suggest: dedupe dual hook registration and make attempt counter per-agent-session'
state: queued
kind: bug
origin: human
created: '2026-09-19'
priority: high
parent: T-5101
tier: ticket
sprint: v0.533.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .claude/settings.json
- tests/test_hook_frob_suggest.py
- tests/test_hook_sync_claude_config.py
- .claude/hooks/sync-claude-config.py
- .claude/hooks/frob-suggest.py
- .claude/hooks/_shellscan.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: .claude/hooks/*
  reason: narrow to avoid lease collision with T-4689
  actor: logan
  at: '2026-09-19'
- op: add
  glob: .claude/hooks/sync-claude-config.py
  reason: files touched for registration dedupe + per-session counter
  actor: logan
  at: '2026-09-19'
- op: add
  glob: .claude/hooks/frob-suggest.py
  reason: files touched for registration dedupe + per-session counter
  actor: logan
  at: '2026-09-19'
- op: add
  glob: .claude/hooks/_shellscan.py
  reason: files touched for registration dedupe + per-session counter
  actor: logan
  at: '2026-09-19'
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.533.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
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
Leaf 1 of T-5101. See scratchpad/HOOK-AUDIT.md section 0b.