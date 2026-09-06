---
id: T-4128
title: 'SCOPE002 doc-closure debt: whole-directory scope on src/frob/_cli_parsers/_ticket/*.py
  leaves dozens of pre-existing symbols undeclared'
state: queued
kind: docs
origin: human
created: '2026-09-06'
priority: medium
blocked_by:
- T-4127
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/_cli_parsers/_ticket/_closeout.py
- src/frob/_cli_parsers/_ticket/_new.py
- src/frob/_cli_parsers/_ticket/_query.py
- src/frob/_cli_parsers/_ticket/_progress.py
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
Found while working T-4106: declaring the whole-directory glob src/frob/_cli_parsers/_ticket/*.py in a ticket's scope (as T-4106's own scope does) surfaces ~44 pre-existing SCOPE002 findings -- symbols in those files whose frob:doc/frob:tests targets live in docs/paths not also in scope. None of these are new; they predate T-4106's diff. Filed separately since closing this doc-closure gap for every such symbol is unrelated to T-4106's own fix (the evidence/criterion cross-verb flag hint) and would badly balloon that ticket's scope. Remedy: either add the missing docs/tests paths to whichever ticket next touches this directory's scope, or decide these edges are stale and remove them. Same class of debt as T-4123 (filed for T-4105's own whole-file scope, ticket_runner package).