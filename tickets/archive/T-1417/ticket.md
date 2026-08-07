---
id: T-1417
title: gate:OPAQUE OPAQUE001 errors in test_ticket_close_own_obligations_t1387.py
  (setattr monkeypatch)
state: done
kind: bug
origin: human
created: '2026-08-01'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/unit/test_ticket_close_own_obligations_t1387.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_ticket_close_own_obligations_t1387.py::TestCloseOwnObligationsForTicket::test_clean_diff_and_no_bump_returns_true
- tests/unit/test_ticket_close_own_obligations_t1387.py::TestCloseRefusesOwnObligationsEndToEnd::test_close_succeeds_once_the_diff_is_actually_clean
designated_repro_test: null
threat: null
component: null
---
Found while verifying T-1402 (unrelated to that ticket's own scope): after
merging main (which had just landed T-1410/T-1387's own obligation-gate
work), an unscoped `frob check --ticket T-1402` shows 7 new gate:OPAQUE
OPAQUE001 errors, all in tests/unit/test_ticket_close_own_obligations_t1387.py
(lines 99, 128, 150, 184, 218, 264, 293) -- each a setattr() monkeypatch
call whose non-literal attribute name is invisible to the static binding
table OPAQUE001 checks.

This file did not exist before T-1410/T-1387 landed and none of its content
was touched by T-1402. It needs either a reasoned `frob:waive OPAQUE001
reason="..."` per site (if the monkeypatch target is genuinely dynamic and
safe) or a rework to a statically-resolvable form.