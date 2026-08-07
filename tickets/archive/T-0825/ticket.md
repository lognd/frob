---
id: T-0825
title: 'strata host: same-principal narrow-deny/broad-allow WRITE_DAC indirection
  understates; privilege-clause grammar gap'
state: done
kind: security
origin: auditor
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/_host_isolation.py
- docs/strata/host.md
- tests/unit/strata/test_host_isolation.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_narrow_deny_then_broad_allow_same_principal_denies
- tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_broad_allow_then_narrow_deny_same_principal_still_denies
- tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_fullcontrol_deny_denies_fullcontrol_allow_no_indirection
- tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_narrow_deny_narrow_allow_same_principal_still_denies
- tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_write_deny_modify_allow_same_principal_still_denies
- tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_deny_for_one_principal_does_not_cancel_another_principals_allow
- tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_no_write_rights_entries_denies
designated_repro_test: null
acceptance:
- text: GIVEN a principal with a narrow deny and a broad allow on one path WHEN the
    join evaluates THEN the WRITE_DAC indirection corner has a recorded disposition
    (bit-level modeling or loud documentation plus a behavior-locking test); GIVEN
    token-privilege classes THEN the grammar-clause decision is recorded
  evidence:
  - tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_narrow_deny_then_broad_allow_same_principal_denies
threat: elevation-of-privilege
component: null
---
T-0792 reviewer finding: with per-principal netting, a same-principal
narrow deny (Modify) plus broad allow (FullControl) nets to
not-write-capable in the model, but real NTFS still grants
WRITE_DAC/WRITE_OWNER through the FullControl allow (the denied Modify
bits do not cover them), so the principal can rewrite the DACL and regain
write -- the model's ONLY understating (fail-open) corner, currently
undocumented. Inexpressible in the single-token RIGHTS vocabulary. Pair
with the disclosed privilege-clause gap (SeImpersonate/SeDebug classes
need a strata-core grammar clause, per the T-0792 module docstring).
Either extend the RIGHTS model to bit-level semantics for the deny join,
or document the corner loudly in the module + host.md and add a fixture
test locking the current (understating) behavior so any future change is
deliberate.