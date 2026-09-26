---
id: T-6533
title: 'SYS113: `via` globs do not match dot-directories (.github/**) so real CI files
  read as parked'
state: queued
kind: bug
origin: agent
created: '2026-09-26'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.534.0
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
- src/frob/strata/_selfconform_kinds.py
- src/frob/strata/_code_binding.py
- tests/unit/strata/test_sys113_dotdir_globs.py
- docs/modules/strata.md
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
Source: logand.app-v2 FROBLEMS.md (peer coordinator report, 2026-09-26, frob 0.531.1.dev332). Reproduction lives in that repo (read-only for frob agents); the frob-side positive control must be a fixture here.

F-399: of 36 SYS113/SELFAUDIT001 errors, two on the `ops` node (capabilities exec/net.connect via `.github/**`) are false: .github/workflows/ci.yml and deploy.yml exist on main. The glob matcher excludes leading dot-directories from `**` (a glob-library default). Deliver: `via` globs match dotfiles and dot-directories (fnmatch/pathspec configured accordingly, or explicit `.`-prefix handling), a fixture with a `.github/workflows/*.yml` via that resolves, and the SYS113 message listing the roots it searched when zero files match.
