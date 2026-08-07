---
id: T-0252
title: 'T-0168 evidence id uses dot instead of :: separator, fails COV003'
state: done
kind: bug
origin: human
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tickets-archive.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestConventionUnitBinding::test_test001_exempts_strata_flow_declarations
designated_repro_test: null
threat: null
component: null
---
Found while working T-0156 (release readiness). tickets-archive.md T-0168 evidence entry 'tests/test_gates.py::TestConventionUnitBinding.test_test001_exempts_strata_flow_declarations' uses a dot between class and method instead of pytest's :: separator, so it never resolves via 'frob test --collect' and COV003 fires on 'frob check'. Pre-existing, unrelated to T-0156's scope (tickets-archive.md not in T-0156 scope). Fix: correct the evidence line to use :: between class and method, matching the real collected node id.
## Done report

Changed: tickets-archive.md -- 3 occurrences of the malformed
Class.method evidence id corrected to the pytest Class::method form.
COV003 confirmed gone (frob check --only coverage exit 0). This was the
last standing frob check error; main is now at zero errors.

Evidence: tests/test_gates.py::TestConventionUnitBinding::test_test001_exempts_strata_flow_declarations
(the exact id the fix makes resolvable; passes).

Filed: none.