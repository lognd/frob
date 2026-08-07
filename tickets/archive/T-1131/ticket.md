---
id: T-1131
title: 'tickets: fail/retire releases leases; doctor flags leases on nonexistent worktrees'
state: done
kind: bug
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- src/frob/app/**
- tests/test_tickets.py
- src/frob/doctor.py
- tests/system/test_cli_doctor.py
- docs/guides/install.md
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/doctor.py
  reason: T-1131's acceptance criterion explicitly requires 'frob doctor reports any
    lease whose worktree path no longer exists and offers requeue' -- doctor.py is
    the only home for that surface, reusing the existing frob.tickets._reconcile.reconcile(apply=False)
    dry-run detection; docs/guides/install.md is where every other DoctorReport field
    is documented
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/system/test_cli_doctor.py
  reason: T-1131's acceptance criterion explicitly requires 'frob doctor reports any
    lease whose worktree path no longer exists and offers requeue' -- doctor.py is
    the only home for that surface, reusing the existing frob.tickets._reconcile.reconcile(apply=False)
    dry-run detection; docs/guides/install.md is where every other DoctorReport field
    is documented
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/guides/install.md
  reason: T-1131's acceptance criterion explicitly requires 'frob doctor reports any
    lease whose worktree path no longer exists and offers requeue' -- doctor.py is
    the only home for that surface, reusing the existing frob.tickets._reconcile.reconcile(apply=False)
    dry-run detection; docs/guides/install.md is where every other DoctorReport field
    is documented
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/modules/tickets.md
  reason: documented record_failure/_fail's new T-1131 requeue behavior in the public-api
    section, per playbook section 6 (update docs in the same change)
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_tickets.py::TestFailCliRequeues::test_fail_requeues_an_in_progress_ticket
- tests/test_tickets.py::TestFailCliRequeues::test_fail_leaves_a_non_in_progress_ticket_state_unchanged
- tests/test_tickets.py::TestFailCliRequeues::test_fail_requires_id_and_summary
- tests/system/test_cli_doctor.py::TestDoctorStaleTicketLeases::test_run_diagnosis_healthy_with_no_stale_leases
- tests/system/test_cli_doctor.py::TestDoctorStaleTicketLeases::test_scan_flags_in_progress_ticket_with_no_lease
- tests/system/test_cli_doctor.py::TestDoctorStaleTicketLeases::test_scan_ignores_live_leased_ticket
- tests/system/test_cli_doctor.py::TestDoctorStaleTicketLeases::test_scan_degrades_to_empty_on_a_malformed_ledger
designated_repro_test: null
acceptance:
- text: GIVEN frob ticket fail records a dead end from a worktree WHEN the worktree
    is subsequently removed THEN the ticket does not stay in-progress holding a stale
    lease; frob doctor reports any lease whose worktree path no longer exists and
    offers requeue
  evidence:
  - tests/system/test_cli_doctor.py::TestDoctorStaleTicketLeases::test_scan_flags_in_progress_ticket_with_no_lease
threat: null
component: null
---
T-1050 today: agent fail-logged a superseded ticket, removed its worktree, and the ticket sat in-progress with a lease on a nonexistent path until the coordinator hand-dropped it. Historical siblings: T-0906 stale lease investigation, wave-9 dead-agent requeues. The lease lifecycle should not depend on a coordinator remembering to sweep.