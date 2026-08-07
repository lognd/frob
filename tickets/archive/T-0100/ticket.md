---
id: T-0100
title: frob:tests directives silently degrade when stacked 3+ or separated from def
state: done
kind: bug
origin: agent
created: '2026-07-17'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/graph/**
- src/frob/lang/**
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_graph.py::TestDsl::test_binds_three_stacked_directives_to_def
- tests/test_graph.py::TestDsl::test_binds_five_stacked_directives_to_def
- tests/test_graph.py::TestDsl::test_directive_separated_from_def_by_non_directive_comment
designated_repro_test: null
threat: null
component: null
---
typani campaign gap report: a stack of 3 frob:tests directives above one test def collapsed to a generic file-level edge losing kind=unit; a 5-stack silently dropped the first 3; directives above non-def statements degrade too. Silent data loss in the obligation graph -- should either work or error loudly.
## Done report

Root cause: _find_following measured its 2-line lookahead from each
comment node's own end line; tree-sitter emits each line comment as a
separate node, so the top of an N>=3 directive stack fell outside the
window and silently fell back to enclosing/bare-file binding. Fix:
comments are grouped into contiguous no-gap runs (_block_ends backward
adjacency scan) and each directive resolves following against the run's
last line, making stack depth irrelevant. T-0044's
following-beats-enclosing priority is untouched and its test matrix
stays green. Two PERF heuristic false positives on the new code are
waived with reviewer-audited reasons (single sort per file flagged by
the function-granularity loop gate; linear backward scan flagged by the
token-count heuristic). Reviewer REJECT round (overlong single-line
waive comments failing E501) resolved by shortening reason text; ruff
and format clean. Evidence: 4 regression tests (3-stack, 5-stack,
sandwiched comment, blank line) plus full graph+lang suites (65 passed
at merge).