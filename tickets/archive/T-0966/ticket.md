---
id: T-0966
title: 'gates: SYS100-102/SYS200-203 rule ids missing from _KNOWN_GATE_RULES (T-0964
  constant-scan fallout)'
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
- tests/test_gates.py::TestCoverageGate::test_cov002_scope_grace_without_same_diff_close_still_fires
- tests/test_gates.py::TestCoverageGate::test_open_scopes_grace_requires_both_root_and_diff
- tests/test_gates.py::TestCoverageGate::test_cov002_scope_grace_covers_ticket_created_and_closed_in_same_diff
designated_repro_test: null
acceptance:
- text: given SYS100/SYS101/SYS102/SYS200/SYS201/SYS202/SYS203 are emitted by the
    production `frob sys audit` invocation (_selfconform.py/_contention.py) but absent
    from _KNOWN_GATE_RULES, when known_gate_rule_ids() is queried before this fix,
    then those seven ids resolve as UNKNOWN (test_every_emitted_rule_literal_is_known
    FAILs without the _KNOWN_ISSUE_ALLOWLIST parking entry); after adding the seven
    entries to _KNOWN_GATE_RULES, the same test PASSes with the allowlist drained
    to empty -- proving the rule ids are reachable from the production sys-audit invocation,
    not merely a pure-function unit test
  evidence:
  - tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known
threat: null
component: null
---
T-0964 extended tests/test_gates.py::TestKnownGateRuleIds.test_every_emitted_rule_literal_is_known to resolve rule=CONST_NAME references (module-level REL_*/SYS_* constants), not just inline rule="..." literals. That extension surfaced a real gap: SYS100 (_selfconform.py:213), SYS101 (_selfconform.py:559), SYS102 (_selfconform.py:630), SYS200 (_contention.py:193), SYS201 (_contention.py:291), SYS202 (_contention.py:341), SYS203 (_contention.py:379) are all real firing rule ids referenced via module-level constants (SYS_UNDECLARED_INTERFACE, SYS_STALE_DESIGN, SYS_UNMODELED_CODE, SYS_DUPLICATE_PORT, SYS_OVERLAPPING_PATH, SYS_SHARED_PIPE, SYS_SHARED_STORE_WRITE) but are absent from _KNOWN_GATE_RULES in src/frob/gates/__init__.py -- add entries for all seven so known_gate_rule_ids() covers them, mirroring the T-0961 fix for the REL26x-REL38x/SYS204 batch. Until fixed, T-0964's drift-lock test carries these seven ids in _KNOWN_ISSUE_ALLOWLIST citing this ticket.