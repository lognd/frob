## Done report

Decomposed the four wave-18 functions that crossed the 60-line ARCH
threshold into cohesive I/O vs decision vs formatting helpers, zero
behavior change:

- src/frob/app/check_runner.py::_try_check_delta_via_daemon split into
  _check_delta_daemon_eligible (decision), _query_check_delta_daemon
  (I/O), _reconcile_daemon_check_result (formatting), and
  _render_and_exit_on_daemon_errors (render/exit) -- addresses ARCH103's
  mixed-concerns finding directly, not just the line count.
- src/frob/app/ticket_runner/_close_cmd.py::_fail split into
  _load_ticket_for_fail (I/O), _record_fail_entry (I/O), and
  _requeue_if_in_progress (decision+I/O).
- src/frob/doctor.py::run_diagnosis split into _diagnose_derived_state
  (locked I/O), _collect_doctor_scans (I/O), and _log_doctor_diagnosis
  (I/O).
- src/frob/tickets/_setters.py::ticket_flow split into
  _load_flow_ticket_universe (I/O), _count_filed_by_day (formatting),
  _count_landed_by_day (I/O), and _build_flow_rows (formatting).

All four public symbols kept their existing frob:tests/frob:doc
directives; the two AFFECT001 findings (run_diagnosis, ticket_flow) are
waived as pure internal extractions with no behavior/doc-contract
change. One new PII012 false positive on _log_doctor_diagnosis (name
signature "diagnosis") waived the same way run_diagnosis's own doc
anchor already is.

### Changed
```
 frob.lock                                |  20 +++
 src/frob/app/check_runner.py             | 111 ++++++++-----
 src/frob/app/ticket_runner/_close_cmd.py | 106 +++++++-----
 src/frob/doctor.py                       | 120 +++++++++++---
 src/frob/tickets/_setters.py             | 119 ++++++++++----
 tickets.md                               | 270 ++++++++++++++++++++++++++++++-
 6 files changed, 603 insertions(+), 143 deletions(-)
```

### Evidence
- `tests/test_app_daemon_proxy.py::TestDifferentialParity::test_check_delta_gates_only_json_daemon_matches_in_process` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestFailCliRequeues::test_fail_requeues_an_in_progress_ticket` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestFailCliRequeues::test_fail_leaves_a_non_in_progress_ticket_state_unchanged` (pytest node id, verified passing when recorded)
- `tests/test_tickets.py::TestFailCliRequeues::test_fail_requires_id_and_summary` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorDerivedStateManifest::test_run_diagnosis_healthy_with_no_derived_state` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorMalformedTicketEdges::test_run_diagnosis_healthy_with_no_malformed_edges` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorStaleTicketLeases::test_run_diagnosis_healthy_with_no_stale_leases` (pytest node id, verified passing when recorded)
- `tests/test_tickets_velocity.py::TestTicketFlow::test_filed_and_landed_counted_per_day` (pytest node id, verified passing when recorded)
- `tests/test_tickets_velocity.py::TestTicketFlow::test_zero_activity_days_are_filled_not_sparse` (pytest node id, verified passing when recorded)
- `tests/test_tickets_velocity.py::TestTicketFlow::test_eta_none_when_queue_not_shrinking` (pytest node id, verified passing when recorded)
- `tests/test_tickets_velocity.py::TestTicketFlow::test_eta_computed_when_queue_shrinking` (pytest node id, verified passing when recorded)
- `tests/test_tickets_velocity.py::TestTicketFlow::test_archived_ticket_still_counts_toward_landed` (pytest node id, verified passing when recorded)
- `tests/test_tickets_velocity.py::TestTicketFlow::test_archived_ticket_still_counts_toward_filed` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 13 passed (from 13 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
