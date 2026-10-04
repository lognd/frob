+++
id = "01M30M6G3Z7V2BV5Q7P18YB0P6"
title = "Two more fixture-drift test doubles missing forwarded kwargs (files, whole_land)"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-21T00:00:00Z"
updated = "2026-09-21T00:00:02Z"
aliases = ["T-5247"]
scope = ["tests/unit/test_ticket_runner_base_forward_t4105.py"]
+++

Found while burning down fresh CI run 35654510898, re-verified on current dev tip. Same class of bug as T-draft-5464244a (test double signature drift, not a production bug): (1) tests/unit/test_ticket_runner_base_forward_t4105.py::TestDoneReportBaseResolution's _fake_shared_check_spawn_fn(root, ticket_id, base=None) no longer matches the real _shared_check_spawn_fn call at src/frob/app/ticket_runner/_verify.py:2235, which now also passes files=... -- TypeError: unexpected keyword argument 'files', breaking both test_default_main_resolves_to_no_base_forwarded and test_non_main_base_ref_is_forwarded. (2) tests/unit/verify/test_drain.py::TestRunDrainAsync's _fake_probe(root, *, quiet, exclude_pid=None) no longer matches the real _probe_land_once call at src/frob/tickets/_leases.py:3089, which now also passes whole_land=... -- TypeError: unexpected keyword argument 'whole_land', breaking test_excludes_its_own_originating_land_pid. Fix: add the missing kwarg (files=None / whole_land=False, matching this same session's T-draft-5464244a fix shape for _force_zero_wait) to both stubs.

Split: tests/unit/verify/test_drain.py's _fake_probe fix is BLOCKED by a live lease collision with in-progress T-5035, which already holds tests/unit/verify/test_drain.py -- removed from this ticket's scope. Whoever picks up T-5035's own file (or a fresh ticket once T-5035 releases the lease) should apply the whole_land=False addition to _fake_probe described above. This ticket now covers only tests/unit/test_ticket_runner_base_forward_t4105.py's files= fix.
