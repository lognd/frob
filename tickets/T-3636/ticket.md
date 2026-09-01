---
id: T-3636
title: DOC012 gate fixture points at stale parser dotted-path after T-3586 split
state: done
kind: bug
origin: human
created: '2026-09-01'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_doc012_promotion.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/test_doc012_promotion.py::TestDoc012PromotedToError::test_undocumented_subcommand_is_now_error
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Run 33480116817, BOTH ubuntu and macOS, deterministic:

  tests/test_doc012_promotion.py::TestDoc012PromotedToError::
  test_undocumented_subcommand_is_now_error
  E  AssertionError: expected a DOC012 finding naming the undocumented
     'gadget' subcommand
  E  assert []

Root cause found via reproduction: T-3586's split of
tests/test_gates.py moved _doc012_fake_parser_factory from
tests.test_gates into tests.conftest, but
tests/test_doc012_promotion.py's _DOC012_PROMOTION_FAKE_CONFIG still
points its "parser =" dotted-path string at the OLD location
("tests.test_gates:_doc012_fake_parser_factory"). doc004's dotted-path
resolver fails silently (logs a WARNING, "could not resolve ...: No
module named 'tests.test_gates'") and doc012_gate then has no parser to
introspect, so it returns zero DOC012 findings instead of the expected
one -- reproduced locally, confirmed via the WARNING log line.

Fix: update the fixture's dotted path to
"tests.conftest:_doc012_fake_parser_factory", matching where T-3586
actually left the helper. Not a detector regression at all -- fix at
the true cause (the fixture's stale path), never weaken the test.