---
id: T-3955
title: shell grammar for ops/**.sh plus starter policy
state: queued
kind: security
origin: agent
created: '2026-09-06'
priority: high
parent: T-3928
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_arch.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given a cost estimate for a shell/tree-sitter-bash grammar addition, when
    this ticket's design step completes, then a go/no-go decision is recorded with
    the estimate
  evidence: []
- text: 'given a go decision, when the grammar lands, then a starter [[policy.pattern]]
    catalogue ships alongside it that flags at minimum: credentials in argv (e.g.
    a password positional/PGPASSWORD-adjacent pattern) and an unguarded rm -rf under
    a documented DRY_RUN gate'
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Convergence 3 of T-3928 (threat-model item 3 + edge/ops item 2, arrived independently). Also relevant to T-3920 item 3 -- cite this ticket there, do not duplicate. FINDING THIS WOULD HAVE CAUGHT: two of four confirmed threat-model findings are structurally invisible to policy today because shell has no frob grammar (Caddyfile too, tracked separately). Edge/ops adds two concrete findings needing nothing else: a database password in pg_dump's argv (a REGRESSION of the identical bug already fixed for rclone in the same file) and an unwrapped destructive rm -rf in a script that documents itself as printing-only under DRY_RUN. THEIR KEY CAVEAT, preserve it: ship a STARTER POLICY CATALOGUE with the grammar, because the grammar alone only makes rules possible, it does not by itself catch anything. Cost this before committing: how many grammars does frob already carry (see LANG_COLLECTORS / lang adapters), and is a shell grammar (tree-sitter-bash or similar) proportionate. Related but distinct from T-3858 (frob:waive inert in no-grammar files is about DIRECTIVES; this is about POLICY over ops/**.sh).