---
id: T-draft-0a4d0959
title: Two more fixture-drift test doubles missing forwarded kwargs (files, whole_land)
state: queued
kind: bug
origin: human
created: '2026-09-21'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/test_ticket_runner_base_forward_t4105.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: tests/unit/verify/test_drain.py
  reason: T-5035 holds a live lease on test_drain.py; splitting to unblock the base_forward_t4105
    half
  actor: logan
  at: '2026-09-21'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while burning down fresh CI run 35654510898, re-verified on current dev tip. Same class of bug as T-draft-5464244a (test double signature drift, not a production bug): (1) tests/unit/test_ticket_runner_base_forward_t4105.py::TestDoneReportBaseResolution's _fake_shared_check_spawn_fn(root, ticket_id, base=None) no longer matches the real _shared_check_spawn_fn call at src/frob/app/ticket_runner/_verify.py:2235, which now also passes files=... -- TypeError: unexpected keyword argument 'files', breaking both test_default_main_resolves_to_no_base_forwarded and test_non_main_base_ref_is_forwarded. (2) tests/unit/verify/test_drain.py::TestRunDrainAsync's _fake_probe(root, *, quiet, exclude_pid=None) no longer matches the real _probe_land_once call at src/frob/tickets/_leases.py:3089, which now also passes whole_land=... -- TypeError: unexpected keyword argument 'whole_land', breaking test_excludes_its_own_originating_land_pid. Fix: add the missing kwarg (files=None / whole_land=False, matching this same session's T-draft-5464244a fix shape for _force_zero_wait) to both stubs.