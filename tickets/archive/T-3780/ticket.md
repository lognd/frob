---
id: T-3780
title: winsync excludes .claude/ from the WSL->Windows mirror
state: dropped
kind: bug
origin: human
created: '2026-09-04'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
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
winrun/winsync (~/bin/winsync, machine-local tooling, not tracked in this repo) both the full-sync exclude list (--exclude '.claude/') and the incremental SCAN=(src tests design invariants pyproject.toml uv.lock frob.toml conftest.py) list omit .claude/ entirely. Any edit to a file under .claude/hooks/ (e.g. _root_write_guard_lib.py, root-write-guard.py, frob-suggest.py, root-cleanliness-detector.py) is silently invisible to winrun -- the Windows mirror keeps serving the last-synced (often stale, pre-session) content, so a hook-logic fix cannot be confirmed via the documented winrun workflow without a manual out-of-band copy into the mirror (verified during T-3777: a genuine escape='' tokenization fix to .claude/hooks/_root_write_guard_lib.py did not take effect across 3 separate winrun re-runs until the file was cp'd directly into /mnt/c/Users/logan/Projects/frob/.claude/hooks/, bypassing winsync). This will block every hook-cluster ticket in the current win32-drain drive (T-3777's own cluster plus any sibling ticket touching .claude/hooks/**) the same way. Fix: add .claude/hooks/** (and any other .claude/* subpath actually meant to be live-edited) to winsync's SCAN list, or drop the .claude/ exclude from the --full path -- whichever preserves the deliberate exclusions (.claude/worktrees/, .claude/settings.local.json, .claude/hooks/state/) this repo's own .gitignore already carries.

## Drop reason
- 2026-09-04: winsync (~/bin/winsync, machine-local tooling, not a repo file) fixed directly by the coordinator: now syncs .claude/hooks via the incremental SCAN and excludes only .claude/worktrees/ instead of all of .claude/. No repo change needed.
