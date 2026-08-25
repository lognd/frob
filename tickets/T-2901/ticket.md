---
id: T-2901
title: 'call_graph: bash bare-word invocation unrecognized by shared token-adjacency
  call detector'
state: queued
kind: bug
origin: human
created: '2026-08-25'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/graph/callgraph.py
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
frob.graph.callgraph's shared call-detection heuristic (_called_names,
src/frob/graph/callgraph.py) recognizes a call only as "identifier
immediately followed by '('" (T-0565's token-adjacency rule). This is
correct for every currently-supported grammar (python/typescript/rust/c/
cpp/kotlin all use parenthesized call syntax) but structurally cannot
recognize a bash function invocation, since bash calls a function the
same way it invokes any other command: a bare word with no parentheses
at all (`foo arg1 arg2`, not `foo(arg1, arg2)`). There is no
call-shaped token sequence in RawSymbol.body_tokens for a bash function
call, ever -- not a bug in frob.lang._walk_bash's own extraction, a real
gap in the shared token-adjacency heuristic itself.

Found while building T-1604 (bash language support): CAPABILITY_CALL_GRAPH
is declared a reasoned KNOWN_GAP for bash (frob.lang._support.
_capability_call_graph_status) rather than a false IMPLEMENTED claim,
citing this ticket.

Fix shape (not attempted here -- out of T-1604's own scope, this is
exactly the "special case belongs in a separate finding" instruction):
extend the shared detector with a per-language "is this token position a
call" predicate, or add a bash-specific bare-word-after-newline/semicolon
heuristic recognizing "identifier at statement-start position" as a
call candidate the same way _called_names recognizes "identifier
immediately followed by '('" for the other six grammars.
