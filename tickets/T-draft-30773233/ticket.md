---
id: T-draft-30773233
title: 'land: touched-path set diffs against main not the land target, scanning ~3800
  files per land'
state: queued
kind: bug
origin: human
created: '2026-09-24'
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
worktree: null
branch: null
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
Measured 2026-09-24 on land T-5354 (and every land in /tmp/land-*.log):
"--allow-cross-ticket set -- this land carries 3784 file(s) OUTSIDE
T-5354's own declared scope". The ticket touched 42 files. The 3784 are
every file dev has changed since main, because
`src/frob/app/ticket_runner/_land_cmd.py` calls `_land_touched_paths(
worktree, ticket_id)` at its two call sites (lines ~676 and ~6411 on
dev) without `target_branch=`, and the helper defaults to "main" (T-4547
kept the default byte-for-byte). Lands target dev
(`_resolve_land_target_branch` / `cfg.ticket_land_branch`).
Consequence: the cross-ticket leakage scan, scope validation and the
Tier-A/self-conformance attribution all walk ~90x too many files on
every land (about 190 s of the ~14 min a successful land costs), and the
CrossTicketLeakage warning is meaningless noise.
Fix: pass the resolved land target branch at both call sites (and any
other `_land_touched_paths` caller); positive control: a worktree one
commit ahead of dev, with dev itself ahead of main by unrelated commits,
must report exactly the one commit's files as touched. Add a lint or
test asserting no caller of `_land_touched_paths` relies on the default.
