---
id: T-0788
title: 'gates: register COMPLIANCE005 in the live rule set and dispatch check_cmpl_registry
  in frob check'
state: done
kind: feature
origin: agent
created: '2026-07-23'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
- src/frob/strata/_compliance.py
- docs/design/registry/compliance.yaml
- src/frob/strata/__init__.py
- src/frob/check/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/strata/__init__.py
  reason: 'COMPLIANCE005 dispatch needs check_cmpl_registry exported from

    src/frob/strata/__init__.py (currently private to _compliance.py, the

    declared-scope file) since every gate consumer in src/frob/gates/__init__.py

    imports strata symbols through the public package, never a private

    submodule directly -- no precedent in this repo for reaching into

    frob.strata._compliance from gates/__init__.py. The "compliance" name also

    needs registering in src/frob/check/__init__.py''s gates-fast _STAGE_GROUPS

    set so the chunked --only loop this playbook mandates actually runs it;

    omitting it would silently exclude COMPLIANCE005 from every agent''s

    sanctioned verification pass while still counting it in _ALL_GATES. Both

    additions are minimal, mechanical, single-purpose lines directly required

    by the ticket''s own stated acceptance criterion (COMPLIANCE005 fires as a

    registered gate rule under frob check) -- not unrelated work folded in.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: src/frob/check/__init__.py
  reason: 'COMPLIANCE005 dispatch needs check_cmpl_registry exported from

    src/frob/strata/__init__.py (currently private to _compliance.py, the

    declared-scope file) since every gate consumer in src/frob/gates/__init__.py

    imports strata symbols through the public package, never a private

    submodule directly -- no precedent in this repo for reaching into

    frob.strata._compliance from gates/__init__.py. The "compliance" name also

    needs registering in src/frob/check/__init__.py''s gates-fast _STAGE_GROUPS

    set so the chunked --only loop this playbook mandates actually runs it;

    omitting it would silently exclude COMPLIANCE005 from every agent''s

    sanctioned verification pass while still counting it in _ALL_GATES. Both

    additions are minimal, mechanical, single-purpose lines directly required

    by the ticket''s own stated acceptance criterion (COMPLIANCE005 fires as a

    registered gate rule under frob check) -- not unrelated work folded in.

    '
  actor: logan
  at: '2026-07-23'
evidence:
- tests/test_gates.py::TestComplianceGate::test_compliance005_registered_in_known_gate_rules
- tests/test_gates.py::TestComplianceGate::test_compliance005_fires_on_deferred_disposition
- tests/test_gates.py::TestComplianceGate::test_compliance005_silent_on_handled_by_and_out_of_scope
- tests/test_gates.py::TestComplianceGate::test_compliance005_missing_registry_dir_is_silent
- tests/test_gates.py::TestComplianceGate::test_compliance005_real_repo_registry_passes
designated_repro_test: null
acceptance:
- text: GIVEN a compliance.yaml entry regressed to deferred or undispositioned WHEN
    frob check runs THEN COMPLIANCE005 fires as a registered, waivable gate rule;
    GIVEN the 17 CMPL units re-dispositioned by T-0607 THEN their entries may cite
    handled_by:COMPLIANCE005 and REG002 accepts it
  evidence:
  - tests/test_gates.py::TestComplianceGate::test_compliance005_fires_on_deferred_disposition
  - tests/test_gates.py::TestComplianceGate::test_compliance005_silent_on_handled_by_and_out_of_scope
threat: null
component: null
---
T-0607 built check_cmpl_registry/COMPLIANCE005 but could not register the rule id in _KNOWN_GATE_RULES nor dispatch the check inside frob check (gates/__init__.py out of its scope) -- the implementer disclosed this and used reasoned out_of_scope dispositions naming COMPLIANCE005 as the compensating control. Until this ticket lands, COMPLIANCE005 is enforcement code invoked by nothing in a real check run (the catalogued-is-not-enforced class, T-0343). Wire the dispatch, register the rule, then flip the 17 dispositions to handled_by:COMPLIANCE005.