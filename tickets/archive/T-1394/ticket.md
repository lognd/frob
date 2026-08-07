---
id: T-1394
title: handler.py's _LazyStdoutHandler/_LazyStderrHandler.stream properties are public
  with no frob:doc edge (COV001 x2)
state: done
kind: bug
origin: human
created: '2026-08-01'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/logging/handler.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/logging.md
  reason: 'SCOPE002: frob:doc anchor for handler.py''s stream properties lives in
    this doc file'
  actor: logan
  at: '2026-08-03'
- op: remove
  glob: docs/modules/logging.md
  reason: 'revert: pulls in whole monolithic doc''s closure (T-1010 precedent); SCOPE002
    is WARN-tier nudge only, not worth ballooning scope for two property anchors'
  actor: logan
  at: '2026-08-03'
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
- tests/unit/test_main_entry.py::TestLazyLogHandlers::test_handler_follows_stream_swap_not_bind_time_capture[stderr]
- tests/unit/test_main_entry.py::TestLazyLogHandlers::test_handler_follows_stream_swap_not_bind_time_capture[stdout]
- tests/unit/test_main_entry.py::TestLazyLogHandlers::test_stderr_handler_never_emits_against_a_closed_captured_stream
designated_repro_test: null
threat: null
component: null
---
Found while working T-1392 (frob check --ticket T-1392 unscoped repo-wide gate:COV read 2 errors throughout). T-1385 landed _LazyStdoutHandler/_LazyStderrHandler and a sibling fix (eb6e4b23, 'fix(logging): point handler.py's frob:doc anchors at a section that exists') already repaired the DOC002 anchor-resolution half, but each class's public 'stream' property still has no frob:doc edge at all (COV001: src/frob/logging/handler.py::_LazyStdoutHandler.stream and ::_LazyStderrHandler.stream). Not in T-1392's scope and not touched by its diff -- either add a frob:doc anchor on each stream property (docs/modules/logging.md#public-api, matching the class-level anchor) or move the property to private if it was never meant to be part of the public surface.