---
id: T-0426
title: Promote REG002/REG003 (dangling handled_by / deferred-to-closed) back to ERROR
  once the REG001 backlog is drained
state: done
kind: security
origin: human
created: '2026-07-20'
priority: medium
parent: T-0343
tier: ticket
sprint: null
scope:
- src/frob/gates/_registry_exhaustiveness.py
- tests/
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_registry_exhaustiveness.py::TestDisposition::test_severity_is_error
designated_repro_test: null
threat: null
component: null
---
T-0343 shipped the registry drift-lock at WARN (user decision 2026-07-20: drain the 1020-entry REG001 backlog slowly in the background, warnings not build-breaking). But REG002 (handled_by names a NONEXISTENT rule) and REG003 (deferred to a CLOSED/MISSING ticket) are ACTIVE FALSEHOODS, not backlog -- an entry claiming enforcement/deferral that is fake. They fire 0 today. Once the REG001 undispositioned backlog is drained (T-0384..T-0392 reconciliation), PROMOTE REG002/REG003 (and REG004 dangling duplicate_of/split, REG005 total-drift) back to ERROR so the anti-lie core has teeth -- a fake disposition must HARD-fail, that was the whole point of the drift-lock. Keep REG001 (undispositioned) at WARN only until the backlog is zero, then it too becomes ERROR (a new undispositioned entry should red immediately once there is no legacy backlog to hide in). Acceptance: after backlog==0, REG001-005 are ERROR; a fixture with a dangling handled_by / deferred-to-closed hard-fails the build.