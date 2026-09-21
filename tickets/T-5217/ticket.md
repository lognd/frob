---
id: T-5217
title: 'LEXCHECK001 new backlog item: _docarch_structural.py::scan_citation_shape
  decides from re.search without a symref'
state: queued
kind: bug
origin: human
created: '2026-09-21'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_docarch_structural.py
- src/frob/gates/_lexical_selfcheck.py
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
Found while burning down fresh CI run 35654510898, re-verified on current dev tip. tests/unit/gates/test_lexical_selfcheck.py::TestLexcheck001::test_supplychain_lexcheck001_backlog_is_empty_t2469 fails: src/frob/gates/_docarch_structural.py:264 scan_citation_shape decides from re.search/match/fullmatch/findall/finditer and builds a symref-less Violation (LEXCHECK001). This must be either fixed at the root (give the Violation a real symref) or added to _KNOWN_SUPPLYCHAIN_LEXCHECK001_BACKLOG with a stated class-(b) reason per this test's own T-2469 precedent -- do not skip/delete the test.