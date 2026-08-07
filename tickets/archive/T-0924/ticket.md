---
id: T-0924
title: '_KNOWN_GATE_RULES missing batch: COMPLIANCE00x/HOST00x/HOST-BLAST/KRB00x/LINT00x/PII00x/RELWAIVE002/THREAT001-005'
state: done
kind: bug
origin: human
created: '2026-07-26'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
- src/frob/strata/_compliance.py
- src/frob/strata/_host_isolation.py
- src/frob/strata/_krb_movement.py
- src/frob/strata/_lint.py
- src/frob/strata/_pii.py
- src/frob/strata/_threat.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known
- tests/test_gates.py::TestKnownGateRuleIds::test_returns_known_rule_id
- tests/test_gates.py::TestKnownGateRuleIds::test_is_frozenset
designated_repro_test: null
threat: null
component: null
---
Found while building T-0901's drift-lock test (a static scan of every
`rule="..."` literal constructed inside `src/frob/gates/**` and
`src/frob/strata/**`, asserting it is a subset of
`frob.gates.known_gate_rule_ids()`).

Beyond the ids T-0903/T-0923 already fixed, the same scan surfaces a
much larger pre-existing batch of rule ids that are real, currently-
constructed Violation-shaped literals but are NOT in `_KNOWN_GATE_RULES`:
COMPLIANCE001-004, HOST001, HOST002, HOST-BLAST, KRB001-004, LINT001-005,
PII001-004, RELWAIVE002, THREAT001-005 (src/frob/strata/_compliance.py,
_host_isolation.py, _audit.py, _krb_movement.py, _lint.py, _pii.py,
_backpressure.py, _circuit_breaker.py, _threat.py).

Unlike the T-0903 batch, a repo-wide grep for `caught_by`/`handled_by`
referencing any of these ids today turns up nothing -- so this class is
not (yet) causing an observed WAIVE002/unresolved-caught_by symptom the
way SYSWAIVE002/THREAT006 were. Still the same listing-omission shape,
and T-0901's new drift-lock test carries an explicit, ticket-cited
allowlist for exactly this batch so the test can land clean without
silently expanding T-0901's own file scope -- this ticket is that
allowlist's paydown target. Fix direction: same as T-0903 -- either add
each id to `_KNOWN_GATE_RULES` with a citing comment, or determine (and
document) that a specific id is intentionally a strata-internal-only
finding rule never meant to be caught_by-resolvable, and drop it from the
drift-lock test's allowlist with that reasoning recorded instead.