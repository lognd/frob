---
id: T-0044
title: 'Comment binder: directive above nested method binds to enclosing class'
state: done
kind: bug
origin: human
created: '2026-07-17'
priority: medium
parent: null
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_graph.py::TestDsl::test_binds_to_nested_method_not_enclosing_class
designated_repro_test: null
threat: null
component: null
---
A frob: directive comment placed immediately above a nested method or property binds to the ENCLOSING CLASS, not the method, because the class span contains the comment and 'enclosing' wins over 'following'. The edge is silently dropped (no error), so the method never clears COV001/TEST001. Three doc-campaign agents (a353eda, aa2686f, a1b18ef) independently hit this. Workaround: place the directive as first line INSIDE the method body. Proper fix: when a comment sits directly above a def/decorator, prefer the FOLLOWING symbol over the enclosing one. See src/frob/graph/dsl.py directive binding / _enclosing_src.