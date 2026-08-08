---
id: T-1821
title: 'TestDescribeRootDirt: two tests fail against current describe_root_dirt output
  shape'
state: done
kind: bug
origin: human
created: '2026-08-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land_git_ops.py
- tests/unit/test_rapid_sweep.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_rapid_sweep.py::TestDescribeRootDirt::test_names_the_real_ticket_from_a_staged_rapid_debt_line
- tests/unit/test_rapid_sweep.py::TestDescribeRootDirt::test_unattributed_when_the_true_author_cannot_be_determined
designated_repro_test: null
threat: null
component: null
---
Discovered while working T-1791 (unrelated scope). tests/unit/test_rapid_sweep.py::TestDescribeRootDirt::test_names_the_real_ticket_from_a_staged_rapid_debt_line and ::test_unattributed_when_the_true_author_cannot_be_determined both fail on a clean worktree at current main tip (post T-1740/T-1699/T-1755 era describe_root_dirt output) -- the rendered dirt description no longer contains the expected 'T-1222'/'unattributed' substrings the tests assert on. Reproduced in isolation, not a test-order/parallelism artifact. Needs someone with _land_git_ops.py in scope to reconcile describe_root_dirt's current output shape with these two tests' expectations.