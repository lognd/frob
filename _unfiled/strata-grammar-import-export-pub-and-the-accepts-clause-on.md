+++
id = "01M2VFD205HMCWNTT48BFGXC9T"
title = "strata grammar: import/export/pub and the accepts clause on cross-module flows (parse-only)"
type = "task"
category = "done"
outcome = "done"
priority = "critical"
reporter = "human"
created = "2026-09-19T00:00:00Z"
updated = "2026-09-19T00:00:02Z"
aliases = ["T-5125"]
scope = ["strata-core/src/parse/**", "docs/strata/surface.md"]

[[acceptance]]
text = "Given a module file using `import a.b as c;`, `export { ... }` and `accepts f from m;`, when parsed by strata-core, then the AST carries import, export and accepts records with their dotted paths and aliases."
bound = false

[[acceptance]]
text = "Given `import tickets.*;` or any wildcard/re-export spelling, when parsed, then the parser reports a syntax error (the form does not exist in the grammar)."
bound = false

[[acceptance]]
text = "Given design/frob.strata and all 7 design/litmus/*.strata files, when parsed after the grammar change, then the parse result is unchanged from before (positive control: a planted new-syntax file parses, the old files are byte-identical in their AST)."
bound = false

[[acceptance]]
text = "Given the D-M9 hierarchy decision, when a module file declares its position in the hierarchy, then the grammar accepts that declaration form and rejects a file that declares it twice."
bound = false

[[acceptance]]
text = "Given `accepts f from <module>` where <module> is NOT imported, when parsed, then it parses: `accepts` takes a module REFERENCE, never an import alias. Positive control: an `accepts` written with an import alias is a parse error."
bound = false
+++

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

## Unblock log
- 2026-09-19: unblocked by T-draft-0bcabfa4 -- D-M9 decided 2026-09-19 19:30 (hierarchy, import up only, flows declared by the lower module, accept down); the grammar leaf's acceptance is updated and it is free to start
