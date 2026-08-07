---
id: T-0792
title: 'strata host windows: multi-ACE ACLs collapse to last-declaration-wins, under-reporting
  movement violations'
state: done
kind: security
origin: auditor
created: '2026-07-23'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/_host_isolation.py
- tests/unit/strata/test_host_isolation.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_single_deny_entry_denies
- tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_single_allow_entry_grants
- tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_narrow_deny_then_broad_allow_same_principal_denies
- tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_broad_allow_then_narrow_deny_same_principal_still_denies
- tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_deny_for_one_principal_does_not_cancel_another_principals_allow
- tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_no_write_rights_entries_denies
- tests/unit/strata/test_host_isolation.py::TestWindowsHostIsolation::test_explicit_deny_acl_flag_does_not_fire_shared_writable_path
- tests/unit/strata/test_host_isolation.py::TestWindowsHostIsolation::test_explicit_deny_acl_flag_fires_when_write_rights_present_elsewhere
designated_repro_test: null
acceptance:
- text: GIVEN two acl entries on the same path (a broad allow after a narrow deny)
    WHEN the movement-impossibility join runs THEN deny-overrides-allow NTFS semantics
    apply (the deny is honored regardless of declaration order) and a violation fires
    where the current last-wins collapse stays silent; SeImpersonate-class token privileges
    get a recorded modeling decision (implement or explicit out-of-scope)
  evidence:
  - tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_single_deny_entry_denies
  - tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_single_allow_entry_grants
  - tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_narrow_deny_then_broad_allow_same_principal_denies
  - tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_broad_allow_then_narrow_deny_same_principal_still_denies
  - tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_deny_for_one_principal_does_not_cancel_another_principals_allow
  - tests/unit/strata/test_host_isolation.py::TestMultiAceDenyOverridesAllow::test_no_write_rights_entries_denies
  - tests/unit/strata/test_host_isolation.py::TestWindowsHostIsolation::test_explicit_deny_acl_flag_does_not_fire_shared_writable_path
  - tests/unit/strata/test_host_isolation.py::TestWindowsHostIsolation::test_explicit_deny_acl_flag_fires_when_write_rights_present_elsewhere
threat: elevation-of-privilege
component: null
---
T-0606 reviewer finding: _owned_paths_by_user collapses multiple ACL entries per path to last-declaration-wins, mirroring the POSIX one-owner convention -- but windows ACLs are multi-ACE by design, and an early deny overridden by a later broad allow silently suppresses a violation the proof system should detect (soundness gap in the direction that matters). Implement real deny-overrides-allow joining across all ACEs per path. Also adjudicate SeImpersonatePrivilege/SeDebugPrivilege-class token privileges: model or record out-of-scope with reason.