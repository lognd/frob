---
id: T-0606
title: 'std.host windows: wire service_account/acl/pipe into HOST001/HOST002 movement-impossibility
  proofs'
state: done
kind: security
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0261
parent: T-0254
tier: ticket
sprint: null
scope:
- src/frob/strata/_host_isolation.py
- src/frob/strata/_scenarios.py
- docs/strata/host.md
- tests/unit/strata/test_host_isolation.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_host_isolation.py::TestWindowsHostIsolation::test_shared_writable_acl_path_and_pipe_fire
- tests/unit/strata/test_host_isolation.py::TestWindowsHostIsolation::test_deny_acl_does_not_fire_shared_writable_path
- tests/unit/strata/test_host_isolation.py::TestWindowsHostIsolation::test_service_with_no_account_is_root_run
- tests/unit/strata/test_host_isolation.py::TestWindowsHostIsolation::test_compromised_windows_service_account_scenario
designated_repro_test: null
acceptance:
- text: GIVEN a windows node whose service_account lacks an acl to a sibling service's
    data dir WHEN HOST001/HOST002 evaluate THEN a movement-impossibility finding (or
    proof) is produced equivalent in strength to the linux path
  evidence:
  - tests/unit/strata/test_host_isolation.py::TestWindowsHostIsolation::test_shared_writable_acl_path_and_pipe_fire
  - tests/unit/strata/test_host_isolation.py::TestWindowsHostIsolation::test_deny_acl_does_not_fire_shared_writable_path
  - tests/unit/strata/test_host_isolation.py::TestWindowsHostIsolation::test_service_with_no_account_is_root_run
  - tests/unit/strata/test_host_isolation.py::TestWindowsHostIsolation::test_compromised_windows_service_account_scenario
threat: elevation-of-privilege
component: null
---
T-0261 landed the Windows std.host manifest surface (service_account/gmsa, service, acl, pipe) but HOST001/HOST002 and build_compromised_user_scenario do not branch on any of it -- a windows-only node produces NO movement-impossibility findings today, so the epic's provability promise is linux-only. Wire the windows fields into the isolation rules and the compromised-user scenario builder, mirroring how the linux runs_as/unit/owns fields feed them (T-0256..T-0259 staging precedent). NOTE: T-0261's Done report references this as T-0606 (ex-draft, id lost at land); drafts do not survive land (T-0577), so this ticket is its real replacement.