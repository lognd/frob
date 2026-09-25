---
id: T-draft-ffda706b
title: 'strata expressiveness: model any scaled system'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
parent: T-draft-a878f025
tier: story
sprint: sysdesign
runs_last: false
milestone: 0.539.0
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
frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its story scaffold, none exists on dev yet"
title: strata expressiveness: model any scaled system
kind: feature
tier: story
parent: T-SYS-EPIC
milestone: 0.539.0
sprint: sysdesign
scope: (none -- story, no direct code scope)
blocked_by: []

Body:

Leaves in this story come from STRATA-EXPRESSIVENESS.md's GRAMMAR proposals only (RULE-ONLY
proposals from the same audit are filed as rule leaves in Stories C-G instead, cross-referenced
by row). Every leaf is grouped by which strata-core/src/parse/grammar_*.rs file it touches, and
where one file collects more surface than a single leaf can carry at <=5 points, leaves are
chained by blocked_by against each other (same-file edits are not scope-disjoint from each
other even though they are scope-disjoint from every other file's leaf). Every leaf's title
line in the body starts with "OWNER-OWNED: strata surface change; owner reviews before
dispatch" per the coordinator correction in SYSDESIGN-INVENTORY.md: any leaf that needs a new
surface word touches strata-core/src/parse and the owner redesigns strata personally.

The `lattice` leaf (T-SYS-A-LATTICE) goes first: it is the single highest-leverage finding in
STRATA-EXPRESSIVENESS.md, and every leaf anywhere in this epic that needs "one more trust/label
rung" (tenancy isolation, compliance zones, environments, multi-region active-active/passive)
is blocked on it, directly or via the environment-axis note folded into the same ticket.
