---
id: T-5125
title: 'strata grammar: import/export/pub and the accepts clause on cross-module flows
  (parse-only)'
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: critical
blocked_by:
- T-5082
parent: T-5081
tier: ticket
sprint: v0.536.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- strata-core/src/parse/**
- docs/strata/surface.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.536.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
designated_repro_test: null
acceptance:
- text: Given a module file using `import a.b as c;`, `export { ... }` and `accepts
    f from m;`, when parsed by strata-core, then the AST carries import, export and
    accepts records with their dotted paths and aliases.
  evidence: []
- text: Given `import tickets.*;` or any wildcard/re-export spelling, when parsed,
    then the parser reports a syntax error (the form does not exist in the grammar).
  evidence: []
- text: 'Given design/frob.strata and all 7 design/litmus/*.strata files, when parsed
    after the grammar change, then the parse result is unchanged from before (positive
    control: a planted new-syntax file parses, the old files are byte-identical in
    their AST).'
  evidence: []
- text: Given the D-M9 hierarchy decision, when a module file declares its position
    in the hierarchy, then the grammar accepts that declaration form and rejects a
    file that declares it twice.
  evidence: []
- text: 'Given `accepts f from <module>` where <module> is NOT imported, when parsed,
    then it parses: `accepts` takes a module REFERENCE, never an import alias. Positive
    control: an `accepts` written with an import alias is a parse error.'
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Grammar only, no semantics. In strata-core/src/parse (grammar_core.rs holds the
existing `module` header at ~line 406-433; lexer.rs holds the token set) add:
  - `import a.b as c;` with dotted module paths (charter D6). No wildcard form
    exists in the grammar at all -- `import a.*` must be a parse error.
  - `export { node X; channel Y; label Z; }` and/or a `pub` marker on a
    declaration. An absent or empty export block is legal and means a fully
    private module.
  - `accepts <flow-name> from <module>;` clause on a node declaration.
Dotted module names accepted in the `module` header. Parse-only: the AST/py
bridge carries the new nodes through, nothing checks them yet. All 7 existing
design/litmus/*.strata files and design/frob.strata must still parse unchanged,
because none of them use the new syntax.
