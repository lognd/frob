---
id: T-draft-fd279281
title: 'frob check default diff base is main while lands target dev: root check reports
  1884 COV002 plus PRE001/SCOPE001 artifacts over the 631-file dev..main diff'
state: queued
kind: bug
origin: human
created: '2026-09-20'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/__init__.py
- src/frob/check/_python.py
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
Measured 2026-09-20 on dev (380 commits ahead of frozen main): a bare 'frob check' on the root diffs against merge-base b10d67a0 with main, so gate:COV reports 1884 COV002 errors, PRE001 and SCOPE001 say 631 files touched with no ticket, and every diff-driven gate measures the whole unlanded sprint rather than the working tree. 'frob check --base dev' is the true baseline. Fix: the diff-driven gates resolve their default base from the same source land resolves its target branch (LandReport.target_branch / the current branch's configured land target), never a hard-coded main; a mismatch between check base and land target is itself a loud finding. Found while coordinating the warning drain.