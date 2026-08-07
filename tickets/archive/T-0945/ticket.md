---
id: T-0945
title: T-0926 frob:tests edges use unresolvable targets (DRIFT002 x2 on main)
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- tests/conftest.py
- tests/unit/test_conftest_parse_reset.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_conftest_parse_reset.py::TestConftestParseReset::test_b_does_not_see_a_leaked_partial_parse
designated_repro_test: null
acceptance:
- text: given the fix, when frob check runs, then gate:DRIFT reports 0 errors
  evidence:
  - tests/unit/test_conftest_parse_reset.py::TestConftestParseReset::test_b_does_not_see_a_leaked_partial_parse
threat: null
component: null
---
Same class as T-0940: T-0926's land carried two frob:tests edges the DRIFT resolver cannot match against the obligation graph -- one used the pytest :: separator instead of the graph's dotted Class.method key, one named a nonexistent module-level test. Repointed both at real dotted node ids.