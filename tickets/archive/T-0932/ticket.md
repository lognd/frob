---
id: T-0932
title: _KNOWN_GATE_RULES missing PARSE002 (src/frob/gates/_parse_failures.py)
state: dropped
kind: bug
origin: human
created: '2026-07-26'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
Found while re-verifying T-0924 after merging main: a concurrently-landed
ticket added `PARSE002` (src/frob/gates/_parse_failures.py:68) as a real,
currently-constructed rule literal, but it was never added to
`_KNOWN_GATE_RULES` (src/frob/gates/__init__.py) -- the same listing-
omission class T-0903/T-0923/T-0901/T-0924 already fixed for other ids.

T-0924's own scope is the specific COMPLIANCE/HOST/KRB/LINT/PII/
RELWAIVE002/THREAT batch; PARSE002 is a new, unrelated gap from a
different landing, so it is filed separately rather than folded into
T-0924's fix. T-0924 records PARSE002 in
`tests/test_gates.py::TestKnownGateRuleIds._KNOWN_ISSUE_ALLOWLIST`
(citing this ticket) so its own drift-lock test can stay green without
silently expanding scope; this ticket is that allowlist entry's paydown
target.

Fix direction: add `"PARSE002"` to `_KNOWN_GATE_RULES` with a citing
comment (same pattern as PARSE001), then remove it from the allowlist.

## Drop reason
- 2026-07-26: folded into T-0924