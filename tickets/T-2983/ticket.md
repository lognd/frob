---
id: T-2983
title: 'gh_io part 1: typed gh seam with named failure modes (no gh, no auth, no GitHub
  remote, rate limit, empty-log-on-failed-job)'
state: done
kind: feature
origin: human
created: '2026-08-26'
priority: high
parent: T-2982
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/ghio.py
- tests/test_ghio.py
- docs/modules/ghio.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gh_io.py
  reason: 'greenfield gh_io seam module: typed Result-returning gh subprocess seam
    per T-2982 part 1'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/test_gh_io.py
  reason: 'greenfield gh_io seam module: typed Result-returning gh subprocess seam
    per T-2982 part 1'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/modules/gh_io.md
  reason: 'greenfield gh_io seam module: typed Result-returning gh subprocess seam
    per T-2982 part 1'
  actor: logan
  at: '2026-08-26'
- op: remove
  glob: src/frob/gh_io.py
  reason: rename gh_io -> ghio per owner naming correction (matches gitio convention)
  actor: logan
  at: '2026-08-26'
- op: remove
  glob: tests/test_gh_io.py
  reason: rename gh_io -> ghio per owner naming correction (matches gitio convention)
  actor: logan
  at: '2026-08-26'
- op: remove
  glob: docs/modules/gh_io.md
  reason: rename gh_io -> ghio per owner naming correction (matches gitio convention)
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/ghio.py
  reason: rename gh_io -> ghio per owner naming correction (matches gitio convention)
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/test_ghio.py
  reason: rename gh_io -> ghio per owner naming correction (matches gitio convention)
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/modules/ghio.md
  reason: rename gh_io -> ghio per owner naming correction (matches gitio convention)
  actor: logan
  at: '2026-08-26'
triage_changes:
- field: parent
  old_value: null
  new_value: T-2982
  reason: 'T-2982 decomposition: seam, reporting, validity'
  actor: logan
  at: '2026-08-26'
evidence:
- tests/test_ghio.py::TestPreflight::test_success
- tests/test_ghio.py::TestJobLog::test_empty_log_for_a_failed_job_is_named
- tests/test_ghio.py::TestJobLog::test_truncated_log_for_cancelled_run
- tests/test_ghio.py::TestPreflight::test_no_gh_no_auth_no_remote_never_crashes
- tests/test_ghio.py::TestPreflightIntegration::test_real_subprocess_seam_against_a_fake_gh_binary
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: f84113a59f395a6b74ace182f4632d6a70eefb11
---
