---
id: T-0312
title: LINT004 remedy text says 'attr flag=<id>' but the real/only escape is a 'waive'
  statement
state: done
kind: bug
origin: auditor
created: '2026-07-19'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/_lint.py
- tests/**
- docs/strata/threat.md
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_lint.py::TestLintKillSwitch::test_risky_capability_with_no_flag_is_lint004
designated_repro_test: null
threat: null
component: null
---
FROBLEMS (aprog-private): LINT004's detail string says 'node <id> holds risky capability kind(s) [...] with no declared attr flag=<id> kill-switch', implying the fix is a strata 'attr flag=<id>;' declaration -- but 'attr flag' is not implemented/documented anywhere (grep -rn 'attr flag' docs/ is empty); the actual working escape is a 'waive "LINT004" reason ... ticket ...;' statement. Fix the message to name the real remedy (waive), or implement attr flag if intended. Trivial message/doc fix. Test: LINT004 detail names the waive escape.