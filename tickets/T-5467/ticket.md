---
id: T-5467
title: 'lang_support: frob.tickets and frob.webapp unregistered in source-tree facet
  audit'
state: queued
kind: bug
origin: agent
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: 3
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
triage_changes:
- field: points
  old_value: null
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-24'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while draining CI run 35951365410 (dev 9e0c89bb19). Failing:
tests/test_lang_support.py::TestPackageAudit::test_real_repo_source_tree_is_fully_registered

unfaceted_packages(src_root) returns ('frob.tickets', 'frob.webapp')
instead of (); both packages exist in src tree but are not registered in
whatever facet/registry list this audit checks against.

frob.webapp is OWNED by another agent (out of touch-scope per this drain's
brief -- do not touch src/frob/webapp/**). frob.tickets registration is
fixable in-scope. This ticket may need to land in two halves, or the
frob.webapp half handed to its owning agent while frob.tickets is fixed
here.
