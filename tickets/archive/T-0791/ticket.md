---
id: T-0791
title: 'strata host: :deny ACL flag path has zero test evidence (deny-overrides verified
  by inspection only)'
state: done
kind: bug
origin: auditor
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/unit/strata/test_host_isolation.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_narrow_deny_then_broad_allow_same_principal_denies
- tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_broad_allow_then_narrow_deny_same_principal_still_denies
designated_repro_test: null
acceptance:
- text: GIVEN an ACL rule carrying the :deny flag on a write-capable RIGHTS value
    WHEN _acl_grants_write evaluates it THEN write_capable is False and a shared-writable-path
    violation does NOT fire; a test constructs the :deny shape explicitly
  evidence:
  - tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_narrow_deny_then_broad_allow_same_principal_denies
  - tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_broad_allow_then_narrow_deny_same_principal_still_denies
threat: null
component: null
---
T-0606 reviewer finding: test_deny_acl_does_not_fire_shared_writable_path uses Everyone:Read (non-write RIGHTS), never an actual :deny flag; _acl_grants_write implements deny correctly by inspection but no test exercises that branch. Add the missing fire/no-fire pair.