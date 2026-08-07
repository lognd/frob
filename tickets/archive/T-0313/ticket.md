---
id: T-0313
title: COV001 frob:doc binder only inspects the nearest preceding comment line, not
  the whole block
state: done
kind: bug
origin: auditor
created: '2026-07-19'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/graph/dsl.py
- tests/unit/graph/test_dsl.py
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/graph/test_dsl.py::TestBlockBinding::test_doc_before_two_ticket_lines_still_binds_via_generic_walker
- tests/unit/graph/test_dsl.py::TestBlockBinding::test_narrow_following_window_propagates_backward_through_run
- tests/unit/graph/test_dsl.py::TestBlockBinding::test_gap_still_breaks_propagation
designated_repro_test: null
threat: null
component: null
---
FROBLEMS (aprog-public): a node with '// frob:doc ...' followed by two '// frob:ticket ...' lines directly above 'node X : trusted {' fired COV001 as if no frob:doc edge existed; nodes with exactly ONE frob:ticket line after frob:doc passed. Reordering so frob:doc is the LAST comment line immediately above the symbol fixed it. Strongly suggests the doc-edge binder only inspects the single nearest preceding comment line, not the whole contiguous comment block (off-by-one in _enclosing_src / RawComment.following lookback). Same subsystem as T-0286/T-0294/T-0309. Fix: bind a frob:doc directive found ANYWHERE in the contiguous comment block above a symbol, regardless of other directive lines between it and the symbol. Test: frob:doc followed by 2 frob:ticket lines above a node still yields the doc edge.