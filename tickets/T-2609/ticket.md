---
id: T-2609
title: land-time new-public-symbol doc/test-edge check does not offset for decorators
state: done
kind: bug
origin: human
created: '2026-08-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- tests/test_ticket_work_and_land_finish.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_ticket_work_and_land_finish.py
  reason: T-2609 needs its designated repro/regression tests colocated with the existing
    TestAssertNewPublicSymbolsHaveDocAndTestEdges class
  actor: logan
  at: '2026-08-25'
evidence:
- tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_a_decorated_new_class_with_directives_above_decorator_not_refused
- tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_a_decorated_new_symbol_with_no_edges_still_refuses_positive_control
designated_repro_test: tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_a_decorated_new_class_with_directives_above_decorator_not_refused
designated_repro_changes:
- old_value: tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_a_decorated_new_public_class_with_directives_above_the_decorator_does_not_refuse
  new_value: tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_a_decorated_new_class_with_directives_above_decorator_not_refused
  reason: reordered commits so test-alone precedes fix commit, enabling a real FAILED_AT_PARENT
    verdict instead of the earlier forced designation
  actor: logan
  at: '2026-08-25'
evidence_changes:
- old_node: tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_a_decorated_new_public_class_with_directives_above_the_decorator_does_not_refuse
  new_node: tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_a_decorated_new_class_with_directives_above_decorator_not_refused
  reason: 'T-2609: shortened test method name for FMT001 (frob:tests directive line
    length)'
  actor: logan
  at: '2026-08-25'
- old_node: tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_a_decorated_new_public_function_with_no_edges_still_refuses_positive_control
  new_node: tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_a_decorated_new_symbol_with_no_edges_still_refuses_positive_control
  reason: 'T-2609: shortened test method name for FMT001 (frob:tests directive line
    length)'
  actor: logan
  at: '2026-08-25'
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 1410c4924d0dc4b350fc42133de17ae9f5b2d810
---
## Problem

Found while working T-2585 -- the land-time new-public-symbol doc/test-edge
check (`_new_public_symbols_in_file_missing_doc_or_test_edge` /
`_frob_directive_block`, T-2114/T-2201, `src/frob/app/ticket_runner/
_land_cmd.py`) refused a land for a decorated top-level class
(`@dataclass(frozen=True)\nclass GateRunReplay:`) whose `frob:doc`/
`frob:ticket`/`frob:tests` directive block sat directly above the
DECORATOR line, even though that placement is accepted everywhere else in
this repo (the graph-based `gate:COV`/`gate:TEST` resolver, which the
`frob.lang` parser's `decorated_definition`/`_effective_node` machinery
already offsets for, had zero complaint about the same placement).

Root cause: `_public_top_level_defs` uses `ast.ClassDef.lineno`, which for
a decorated class is the `class` keyword's own line, not the decorator's.
`_frob_directive_block` then walks upward from THAT line looking for a
contiguous comment run -- for a decorated symbol, the line immediately
above `class`/`def` is the decorator itself (not a comment), so the walk
stops immediately and the directive block reads empty regardless of what
comments sit above the decorator.

Workaround used in T-2585: moved the directive comments to between the
decorator and the `class` line instead of above the decorator. Not fixed
at the root -- this land-time check's `ast`-lineno handling needs a
decorator-aware start point (e.g. `node.decorator_list[0].lineno` when
decorators are present, matching what `frob.lang`'s own graph-based parser
already does for the SAME question).

## Suggested direction

In `_public_top_level_defs` (or a caller), when `node.decorator_list` is
non-empty, walk `_frob_directive_block` from the FIRST decorator's lineno
instead of the class/def's own lineno -- same fix shape `frob.lang`'s
`_effective_node` already applies for its own directive-to-symbol binding,
just not yet ported to this separate, land-time-only text scan.