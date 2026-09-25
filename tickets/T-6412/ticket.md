---
id: T-6412
title: 'SYSDESIGN409: single migration both adds a required NOT NULL column and drops/renames
  an old one'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
parent: T-6410
tier: ticket
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
scope:
- src/frob/sysdesign/_migrations.py (new)
- tests/fixtures/sysdesign/sysdesign409/**
scope_breadth_ack: true
scope_breadth_ack_reason: sysdesign epic tree, scope reviewed by coordinator
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
title: SYSDESIGN410: single migration both adds a required NOT NULL column and drops/renames
       an old one, unsafe for rolling/canary deploys
kind: feature
tier: leaf
parent: T-SYS-SF
milestone: 0.539.0
sprint: sysdesign
points: 3
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its story scaffold" -->
scope: src/frob/sysdesign/_migrations.py (new), docs/modules/gates.md (SYSDESIGN410 row),
       tests/fixtures/sysdesign/sysdesign410/**
blocked_by: []
tag: Static: code

Research row 7.10 (no primary-source verbatim quote this pass; a widely documented pattern,
flagged as a citation gap in-row). Lint condition: "A single migration that both adds a new
required (NOT NULL, no default) column and removes/renames an old one in the same deploy flags
as unsafe for rolling/canary deploys."

Confirmed NONE by SYSDESIGN-INVENTORY.md's direct grep: "`git grep -i 'migration'`... none of
these are a DB-schema expand/contract SYSDESIGN check. No grammar token, no rule id."

Acceptance criteria: parses migration files (Alembic/Django/Rails-shaped) in one changeset;
flags a migration adding a NOT NULL column with no default in the same file as one dropping or
renaming a column. Positive-control fixture: tests/fixtures/sysdesign/sysdesign410/
add-notnull-drop-column-same-migration/**.
