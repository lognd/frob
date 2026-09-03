---
id: T-3601
title: add control-flow fixtures for frob-suggest ack-on-first-block (T-3071)
state: done
kind: docs
origin: human
created: '2026-08-31'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_hook_frob_suggest.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/test_hook_frob_suggest.py::test_ack_prefixed_first_attempt_is_allowed_through
- tests/test_hook_frob_suggest.py::test_unacked_first_attempt_is_still_blocked
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-3071 fixed the first-block/FROB_SUGGEST_ACK gap in .claude/hooks/frob-suggest.py but T-3071's own scope was the hook file only, so tests/test_hook_frob_suggest.py was not touched. Add must-stay-quiet/must-fire fixtures for: (1) FROB_SUGGEST_ACK=1 <command> passes on the FIRST encounter of that command string, (2) the same command WITHOUT the ack is still blocked on first encounter. Manually verified both behaviors via direct hook invocation while landing T-3071; this ticket is the missing automated coverage the ticket's own acceptance criteria called for.