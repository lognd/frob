---
id: T-0547
title: 'gates: name-only test-convention match credits unrelated same-named symbols
  (B6)'
state: done
kind: bug
origin: auditor
created: '2026-07-21'
priority: medium
parent: T-0403
tier: ticket
sprint: null
scope:
- src/frob/gates/
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestTest014AmbiguousConventionMatch::test_fires_on_cross_file_same_test_collision
- tests/test_gates.py::TestTest014AmbiguousConventionMatch::test_silent_when_symbol_has_explicit_edge
- tests/test_gates.py::TestTest014AmbiguousConventionMatch::test_silent_when_no_leaf_name_collision
designated_repro_test: null
threat: null
component: null
---
docs/audits/gates-accounting.md B6. _inferred_unit_cases matches by snake-cased leaf name only, no module/path binding. Two different public functions both named parse (different modules) are both covered by one test_parse that exercises only one. Repro: two def parse() in different files, one test_parse -> both clear TEST001. RIGHT-WAY fix direction: require some path/module correlation between the test file and the symbol's file before the naming-convention fallback applies. Risk: repo does not strictly mirror tests-to-src layout everywhere -- needs a compat survey before tightening, too large for the T-0403 sweep budget.