---
id: T-1162
title: 'arch: wave-18 fallout long-function extractions (check_runner delta-proxy,
  close _fail, doctor run_diagnosis, setters ticket_flow)'
state: done
kind: bug
origin: human
created: '2026-07-28'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/check_runner.py
- src/frob/app/ticket_runner/_close_cmd.py
- src/frob/doctor.py
- src/frob/tickets/_setters.py
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_app_daemon_proxy.py::TestDifferentialParity::test_check_delta_gates_only_json_daemon_matches_in_process
- tests/test_tickets.py::TestFailCliRequeues::test_fail_requeues_an_in_progress_ticket
- tests/test_tickets.py::TestFailCliRequeues::test_fail_leaves_a_non_in_progress_ticket_state_unchanged
- tests/test_tickets.py::TestFailCliRequeues::test_fail_requires_id_and_summary
- tests/system/test_cli_doctor.py::TestDoctorDerivedStateManifest::test_run_diagnosis_healthy_with_no_derived_state
- tests/system/test_cli_doctor.py::TestDoctorMalformedTicketEdges::test_run_diagnosis_healthy_with_no_malformed_edges
- tests/system/test_cli_doctor.py::TestDoctorStaleTicketLeases::test_run_diagnosis_healthy_with_no_stale_leases
- tests/test_tickets_velocity.py::TestTicketFlow::test_filed_and_landed_counted_per_day
- tests/test_tickets_velocity.py::TestTicketFlow::test_zero_activity_days_are_filled_not_sparse
- tests/test_tickets_velocity.py::TestTicketFlow::test_eta_none_when_queue_not_shrinking
- tests/test_tickets_velocity.py::TestTicketFlow::test_eta_computed_when_queue_shrinking
- tests/test_tickets_velocity.py::TestTicketFlow::test_archived_ticket_still_counts_toward_landed
- tests/test_tickets_velocity.py::TestTicketFlow::test_archived_ticket_still_counts_toward_filed
designated_repro_test: null
acceptance:
- text: GIVEN frob check --only arch THEN zero ARCH001/ARCH103 errors remain at the
    four wave-18 sites (_try_check_delta_via_daemon 70 lines + mixed concerns, _fail
    73, run_diagnosis 99, ticket_flow 86), each decomposed into cohesive helpers with
    existing tests still passing
  evidence:
  - tests/test_app_daemon_proxy.py::TestDifferentialParity::test_check_delta_gates_only_json_daemon_matches_in_process
threat: null
component: null
---
The only remaining errors on main after the wave-18 fallout pass: four functions grew past the 60-line threshold in this wave's lands (T-1147, T-1131/T-1132, T-1142/T-1151). Standard extraction discipline; ARCH103 on _try_check_delta_via_daemon wants the I/O vs formatting vs decision split, not just a length cut.