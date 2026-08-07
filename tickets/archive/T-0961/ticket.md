---
id: T-0961
title: gates/__init__.py _KNOWN_GATE_RULES missing the bulk of the REL26x-REL38x +
  SYS204 obligation-family rule ids
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known
- tests/test_gates.py::TestKnownGateRuleIds::test_returns_known_rule_id
designated_repro_test: null
acceptance:
- text: 'FAIL before this ticket''s fix: tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known
    would newly flag REL201/REL210/REL211/REL222/REL230/REL231/REL240/REL241/REL250/REL261/REL271/REL281/REL290/REL291/REL300/REL301/REL310/REL311/REL321/REL331/REL340/REL351/REL360/REL371/REL372/REL380/REL381/REL382/REL383/SYS204
    as unknown the moment any one of them were exercised through a `rule="..."` literal
    (they were reachable only via named `REL_*`/`SYS_*` constants, so the drift-lock
    could not see them at all -- itself the bug), and separately `known_gate_rule_ids()`
    (the production surface `frob check`/`frob sys audit` actually consult to accept
    or reject a rule id) did not contain them. PASS after this ticket''s fix: all
    30 ids are members of `known_gate_rule_ids()` (frob.gates._KNOWN_GATE_RULES),
    and the same drift-lock test (tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known)
    passes with `_KNOWN_ISSUE_ALLOWLIST` empty, proving the fix through the production
    `known_gate_rule_ids()` invocation the real gate pipeline uses, not a bare unit
    test of the frozenset literal alone.'
  evidence:
  - tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known
threat: null
component: null
---
Filed while working T-0958 (system-design.yaml reconciliation). T-0958 added exactly the 11 REL2xx/REL3xx rule ids it needed for its own handled_by dispositions (REL200/220/221/260/270/272/280/320/330/350/370) to gates/__init__.py's _KNOWN_GATE_RULES frozenset, but the REL26x-REL38x epic (T-0331's landed obligation families) shipped roughly two dozen more rule ids that were never added there either -- the same listing-omission class T-0903/T-0923/T-0924 already fixed for other batches. Known gap at filing time (non-exhaustive): REL201, REL210, REL211, REL222, REL230, REL231, REL261, REL271, REL281, REL290, REL291, REL300, REL301, REL310, REL311, REL321, REL331, REL340, REL351, REL360, REL371, REL372, REL380, REL381, REL382, REL383, and SYS204. Fix: audit every REL_MISSING_*/REL_UNPROVEN_*-shaped constant across src/frob/strata/*.py plus SYS204 (frob.strata._contention) against _KNOWN_GATE_RULES and add every one actually missing, mirroring T-0903/T-0923/T-0924's own precedent comments.