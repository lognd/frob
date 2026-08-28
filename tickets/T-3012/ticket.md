---
id: T-3012
title: Rust symbol resolution does not cover impl-block methods (DRIFT002/frob:tests)
state: dropped
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

## Drop reason
- 2026-08-28: Premise falsified -- measured directly, not inferred.

parse_file() on the exact file the ticket names
(strata-core/src/graph/model.rs) correctly extracts Graph.add_node and
Graph.add_node_with_attrs as SymbolKind.METHOD RawSymbols (impl-block
methods, dot-joined qualname): src/frob/lang/_walk_rust.py's _visit
already recurses into impl_item via _recurse_impl (in_impl=True), and
_function_symbol assigns SymbolKind.METHOD when in_impl is set. This is
NOT a "free functions only" gap.

build_graph() over the WHOLE repo confirms the same key resolves in the
live snapshot: "strata-core/src/graph/model.rs::Graph.add_node" in
snap.symbols -> True (27590 symbols, 29110 edges, 0 malformed, 0 parse
failures -- frob-core/strata_core natives built and importable for this
measurement, ruling out a stale/missing-native false reading).

Round-tripped a synthetic frob:tests directive end-to-end (parse_file +
parse_directives + build_graph, the actual DRIFT002 substrate
_vanished_endpoint reads): "frob:tests src/graph.rs::Graph.add_node
kind=\"unit\"" resolved cleanly to a TESTS edge with ZERO DRIFT002
findings when the target uses this repo's dot-joined qualname
convention.

Root cause of the reporter's actual DRIFT002 hits: both forms they
tried -- "Graph::add_node" (Rust's own native path separator) and bare
"add_node" (no type qualifier at all) -- are LITERAL STRING MISMATCHES
against the real key "Graph.add_node", not a resolver gap. This is the
identical, already-documented T-0265 convention mismatch
(frob.graph.dsl._parse_line's own inline comment: "the directive's
target string uses pytest's Class::method collect-only separator while
the graph's own qualname is Class.method") -- previously observed for
Python's pytest collect-only syntax, now the same mistake recurring for
Rust's native `::` path syntax. DRIFT002 firing here is CORRECT,
intended behavior (catching a broken directive target), not a false
negative letting an unresolvable directive through silently.

"Zero existing frob:tests/frob:doc directives point at a Rust impl-block
method anywhere in this repo" (the ticket's own supporting evidence) is
real and reproducible (git grep confirms it), but it is evidence of a
real, live ergonomics gap of a DIFFERENT shape than what this ticket
describes: nothing surfaces the correct `.`-separator convention to a
Rust-directive author before they hit DRIFT002, and DRIFT002's own
message ("no candidates found") does not suggest the `::`-to-`.` fix.
That is a documentation/error-message clarity gap, not a symbol-
resolution defect in frob-core/src/extract.rs or its Python-side
resolver -- this ticket's own declared scope and Plan (extend the Rust
extraction query to emit impl-block methods) targets code that already
works correctly, so implementing it as scoped would be a no-op change
to already-correct logic.

Not filing a follow-up here: a docs/error-message ergonomics ticket for
the ::-vs-. convention gap is a genuinely different, smaller unit of
work than what T-3012 describes, and outside my series' scope (DETECTOR
ACCURACY covers misfires/misses, not documentation). Leaving that
observation in this drop record for whoever triages it next.
