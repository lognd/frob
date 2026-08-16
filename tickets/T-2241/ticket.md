---
id: T-2241
title: Add frob sync-skills subcommand; retire Makefile bash bidirectional sync loop
state: queued
kind: feature
origin: human
created: '2026-08-16'
priority: medium
parent: T-1382
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/scaffold/_skills_sync.py
- src/frob/_cli_parsers/**
- tests/unit/test_skills_sync.py
- Makefile
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: 'GIVEN no Makefile WHEN ''uv run frob sync-skills'' runs on a repo with agents/
    and skills/ directories THEN it bidirectionally syncs them into ~/.claude/agents
    and ~/.claude/skills the same way the old sync-skills: recipe did, including removing
    stale entries no longer present in the repo'
  evidence: []
- text: GIVEN Windows (no bash, no POSIX for/basename/test) WHEN the sync runs THEN
    it uses only pathlib/shutil, no shelled-out bash loop
  evidence: []
- text: 'GIVEN the Makefile WHEN read THEN sync-skills: is a single ''uv run frob
    sync-skills'' line'
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
---
Makefile's sync-skills: target (Makefile lines ~566-601) is a ~35-line bash recipe: two POSIX for-loops over agents/*/ and skills/*/ doing mkdir -p/cp -r into $(HOME)/.claude, plus two more for-loops removing stale entries under ~/.claude that no longer exist in the repo. This has no frob equivalent today (git grep -n 'sync-skills|sync_skills' src/ tests/ returns nothing) and is pure POSIX shell -- for, basename, [ -d ], cp -r -- none of which exist on a bare Windows shell. This is real logic (bidirectional diff-and-remove, not just a copy), so it needs an actual Python implementation, not a thin wrapper. First test that must fail today: 'uv run frob sync-skills --help' (no such subcommand exists). MUST-STILL-PASS: after migration, an existing ~/.claude/agents or ~/.claude/skills entry with no repo-side counterpart is still removed (stale-entry cleanup), and a repo-side agents/skills addition still appears under ~/.claude after running the new subcommand -- same net filesystem effect as today's bash loop, verified by a test using a temp HOME rather than the real one. Related but out of scope note: CLAUDE.md's stated intent to rework/remove agents/ and skills/ entirely is a SEPARATE decision for the ticket owner, not assumed here; this leaf only removes the Makefile/bash dependency of whatever sync mechanism exists at land time.