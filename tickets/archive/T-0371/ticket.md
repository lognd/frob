---
id: T-0371
title: 'TEST001: collect_file_dispatch_refs missing unit test binding'
state: done
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/arch/_python.py
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_arch.py::TestDispatchFamilySuppression::test_dispatch_family_no_abstraction_opportunity
designated_repro_test: null
threat: null
component: null
---
Found while working T-0365 (unrelated to TEST006/TEST009 scope). frob check --only test reports: TEST001 src/frob/arch/_python.py:365 collect_file_dispatch_refs is public with no unit test. Introduced by T-0360 (fix(arch): make dispatch-family linking structural, not textual). Needs a frob:tests directive (or a test named test_collect_file_dispatch_refs) binding this function.