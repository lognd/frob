---
id: T-3012
title: Rust symbol resolution does not cover impl-block methods (DRIFT002/frob:tests)
state: in-progress
kind: bug
origin: human
created: '2026-08-26'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- frob-core/src/extract.rs
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
## Description

Rust symbol extraction (used by DRIFT002/frob:tests resolution, and
presumably COV001/TEST001 gates) does not resolve `impl Type { fn method
}` paths -- only free functions at module scope. Confirmed while working
T-3005 (strata-core::graph): every `frob:tests strata-core/src/graph/
model.rs::Graph::add_node` (or bare `add_node` inside an impl block)
directive I added produced DRIFT002 "no candidates found", and grepping
the whole repo found zero existing `frob:tests`/`frob:doc` directives
anywhere pointing at a Rust impl-block method -- consistent with this
being a standing gap, not something specific to my directive syntax.

Practical effect: any Rust crate that organizes its public API as struct
methods (idiomatic Rust, and what strata-core::graph does) cannot get
TEST001/COV001 coverage-gate credit for those methods, and cannot bind a
frob:tests edge to them at all -- the directive is accepted at parse
time but permanently unresolvable. Free top-level fns (e.g.
parse_source, reachable in strata-core/src/lib.rs) resolve fine.

## Plan

Find the Rust tree-sitter/extraction query behind DRIFT002/COV gates
(frob-core's extract_tree_rust and whatever py-side resolver consumes its
symbol table) and extend it to emit a qualified Type::method (or
equivalent) symbol for impl block members, matching how free functions
already resolve.

## Scope

- frob-core/src/extract.rs (extract_tree_rust and friends)
- whatever Python-side resolver maps a Rust symbol name to a DRIFT002/
  COV001/TEST001 candidate (grep from there)
