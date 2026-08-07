---
id: T-0902
title: Add PARSE002 gate wiring partial_parse_files() into frob check + regression
  test
state: done
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_parse_failures.py
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestParseFailureGate::test_partial_parse_is_an_error_violation
- tests/test_gates.py::TestParseFailureGate::test_no_partial_parses_is_clean
- tests/test_gates.py::TestParseFailureGate::test_no_parse_failures_is_clean
- tests/test_gates.py::TestParseFailureGate::test_parse_failure_is_an_error_violation
designated_repro_test: null
threat: null
component: null
---
Found while working T-0786 (gate-vacuousness sweep), pairs with the
PARSE002 (partial-parse) fix ticket.

Bind a regression test asserting `frob.lang.partial_parse_files()` is
actually consumed by `frob check`'s gate dispatch (e.g. a fixture with a
syntax error partway through a file, asserting the missing tail symbol's
COV001 obligation is NOT silently dropped, and that a PARSE002-shaped
violation fires). This closes the "queryable accessor with zero consumers"
class of gap the same way T-0558 closed it for hard parse failures.