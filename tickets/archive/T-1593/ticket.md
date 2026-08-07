---
id: T-1593
title: 'ARCH001: split _land_core, _check_mutation_evidence, run_pending_sweep along
  T-1518''s stage seams'
state: done
kind: feature
origin: human
created: '2026-08-05'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/tickets/_land.py
- src/frob/tickets/_mutation_sweep_queue.py
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_mutation_sweep_queue.py::TestRunPendingSweep::test_empty_queue_is_noop
- tests/unit/test_mutation_sweep_queue.py::TestRunPendingSweep::test_clean_finding_marks_swept_no_ticket_filed
- tests/unit/test_mutation_sweep_queue.py::TestRunPendingSweep::test_bug_kind_confirmatory_finding_files_ticket
- tests/unit/test_mutation_sweep_queue.py::TestRunPendingSweep::test_non_bug_confirmatory_finding_only_warns
- tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_confirmatory_test_flagged
- tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_adversarial_test_not_flagged
- tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_no_test_evidence_is_ok_empty
- tests/unit/test_ticket_runner_land_release.py::TestApplyReleaseBumpForLand::test_bump_applies_writes_and_stamps
- tests/test_ticket_land.py::TestLand::test_dry_run_lands_cleanly_and_leaves_no_trace
- tests/test_ticket_land.py::TestLand::test_real_land_lands
designated_repro_test: null
threat: null
component: null
---
Three functions landed over the ARCH001 60-line threshold during wave 6 and are the only gate errors on main:

- src/frob/app/ticket_runner/_land_cmd.py::_land_core -- 162 lines
- src/frob/tickets/_land.py::_check_mutation_evidence -- 133 lines
- src/frob/tickets/_mutation_sweep_queue.py::run_pending_sweep -- 98 lines

All three grew from T-1518 (TEST016 off the land critical path) and T-1575 (profiles), which added branching to already-long functions rather than splitting them.

_land_core is the worst and the most load-bearing: it is the whole land pipeline in one body (precheck, evidence checks, merge, sweeps, REL001, ledger splice, LAND-PROOF). T-1518 defined stage seams for exactly this reason -- extract along those seams so each stage is independently readable and testable, not by cutting arbitrary 60-line chunks.

_check_mutation_evidence should split its profile/kind decision (does this ticket owe synchronous mutation evidence at all?) from the running and classifying of the mutation subprocess.

run_pending_sweep should split queue draining from per-entry execution.

Do not waive these. ARCH001 has an escape hatch, but a 162-line land pipeline is the genuine article the rule exists to catch, and this repo has already paid for hard-to-follow land code several times this drive.