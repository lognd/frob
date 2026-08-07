---
id: T-0161
title: 'PERF001-004 lexical heuristic: false-positive classes need real fixes, not
  permanent waivers'
state: done
kind: bug
origin: human
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/perf/**
- tests/**
- docs/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_perf.py::test_perf003_fires_on_nested_join_with_intervening_statement
- tests/test_perf.py::test_perf003_does_not_fire_on_sibling_comprehensions
- tests/test_perf.py::test_perf003_does_not_fire_on_sibling_statement_loops
- tests/test_perf.py::test_perf004_does_not_fire_when_sorted_is_the_loop_iterable
designated_repro_test: null
threat: null
component: null
---
found while working T-0148: the gates sweep waived 93 PERF001-004 sites (14 PERF001, 8 PERF002, 52 PERF003, 19 PERF004) as false positives of src/frob/perf/_rules.py's documented 'lexical, one-token-stream-deep linear-scan' heuristic. Every waived site fell into one of a small number of misfire classes, each fixable without a full AST/control-flow rewrite: (1) PERF003 'nested loop join' fires on ANY function body containing 2+ 'for' headers plus an '==' comparison ANYWHERE in the body, even when the two loops are separate siblings (a setup loop then an unrelated assertion loop) rather than actually nested -- needs real nesting-depth tracking, not a flat token count over the whole function. (2) PERF004 'sorted()/.sort() in a loop' fires on any sorted()/.sort() call that is lexically inside an enclosing for/while, even when it executes exactly once per function call (e.g. sorting a small already-collected result list right before returning) -- needs to distinguish 're-sorted every outer iteration' from 'lexically nested but reached once'. (3) PERF001 'membership test in a loop' (confirmed in strata-core/src/lib.rs) fires on 'x in <name>' with zero awareness of the collection's actual type -- a HashSet/HashMap membership test is O(1) and not a smell at all, but the heuristic cannot tell a HashSet from a Vec since it never sees types. (4) PERF002 similarly flags any .index()/.count() call lexically inside a loop regardless of whether it runs once per call. Deliverables: either (a) add lightweight scope/nesting tracking to the existing token-stream scanner (track brace/indent depth per 'for' header, require the '==' to be textually inside the INNER loop's body, not just anywhere after the outer loop opens; require sorted()/.sort()/.index()/.count() calls to be inside the loop body they are nested under AND for that enclosing loop to actually repeat the call across iterations rather than short-circuiting via return/break), or (b) for languages with type info available (Rust via the existing AST, TypeScript via its checker) consult the declared/inferred type of the container before firing PERF001/PERF002. Re-run the current 93 waived sites (grep 'frob:waive PERF00' across the repo for the exact list, dated 2026-07-18, T-0148) against the improved rules and either remove now-unnecessary waivers or downgrade them to genuinely-irreducible cases. Acceptance: fewer than half of the current 93 waivers remain necessary, and no new false-positive class is introduced (verified against this repo's own PERF-clean modules).