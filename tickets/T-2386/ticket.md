---
id: T-2386
title: 'sync-skills: provenance-aware sync to stop cross-repo agents/skills deletion'
state: queued
kind: bug
origin: human
created: '2026-08-17'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/scaffold/_skills_sync.py
- tests/unit/test_skills_sync.py
- docs/commands/sync-skills.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Child of T-2384 (sync-skills half). _sync_one_kind currently rmtree's every
~/.claude/<kind>/<name> with no repo-side counterpart, and copytree's in
with dirs_exist_ok=True unconditionally. Two frob-enabled repos sharing one
~/.claude flap/destroy each other's agents and skills.

Fix: provenance manifest at <claude_dir>/.frob-sync-manifest.json keyed by
repo identity (resolved repo_root path), recording which <kind>/<name>
entries THIS repo installed. Removal is restricted to entries this repo's
own manifest previously recorded that are now absent repo-side -- never an
entry owned by another repo or never-synced (hand-maintained). Copy-in
refuses (collision, reported, not silently overwritten) when the
destination exists and is not already owned by this repo's manifest,
unless --force.

Acceptance (from T-2384):
[1] two repos syncing into the same ~/.claude never remove/overwrite each
    other's entries; running either sync twice in a row is a no-op the
    second time.
[2] a ~/.claude with hand-maintained agents/skills, first sync run:
    nothing deleted, nothing overwritten (reported as collision instead).

All tests exercise a tmp_path --claude-dir, never the real ~/.claude.