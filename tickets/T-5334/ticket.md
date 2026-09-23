---
id: T-5334
title: 'SQL substrate: literal extraction from host languages + sqlfluff relevance'
state: in-progress
kind: feature
origin: human
created: '2026-09-22'
priority: high
blocked_by:
- T-5302
- T-5307
parent: T-5148
tier: ticket
sprint: null
runs_last: false
milestone: 0.534.0
points: 5
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/sql/_extract.py
- tests/fixtures/sql/**
- frob.toml
- docs/modules/sql.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: frob.toml
  reason: 'sql/_extract.py imports frob.lang.raw_tree/child_by_field/node_text, so
    sql needs its own [arch.layering.allow] entry for lang (T-5302 precedent: webapp=[''lang''])'
  actor: logan
  at: '2026-09-23'
- op: add
  glob: docs/modules/sql.md
  reason: new public module needs its own docs/modules/*.md, cited from frob:doc directives
    in _extract.py
  actor: logan
  at: '2026-09-23'
triage_changes:
- field: points
  old_value: null
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: milestone
  old_value: null
  new_value: 0.534.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-23'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5334
branch: t-5334
---
tree-sitter AST walk (Python for cursor.execute/.raw()/SQLAlchemy text(); TS for Prisma queryRaw/sqlx macros) extracting string literals and f-string/template skeletons passed to known SQL-executing call sites, feeding sqlfluff's parser; any non-literal string composition reaching a sink is itself a WEBSEC-class injection finding -- this leaf calls into 5141-1's sink registry rather than re-detecting, EXCEPT psycopg.sql composition (a safe API, explicitly excluded per the corpus). OWNER DIRECTIVE: this leaf's relevance predicate (a .sql file OR an SQL-executing call site exists in the repo) is what makes sqlfluff REQUIRED-for-the-family in 5148-2's tool-registry entry -- define the predicate here as a reusable function so 5148-2 imports it rather than re-detecting. Fixture: one extraction case per host-language/ORM call shape.