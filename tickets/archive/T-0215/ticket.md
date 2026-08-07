---
id: T-0215
title: non-pytest evidence channel for docs/design tickets + close-from-queued hint
state: done
kind: feature
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- src/frob/app/**
- src/frob/gates/__init__.py
- tests/**
- docs/modules/tickets.md
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_tickets_cmd_evidence.py::TestCmdEvidence::test_exit_zero
- tests/test_tickets_cmd_evidence.py::TestCmdEvidence::test_nonzero_exit
- tests/test_tickets_cmd_evidence.py::TestCmdEvidence::test_same_output_is_deterministic
- tests/test_tickets_cmd_evidence.py::TestKindGate::test_bug_kind_rejected
- tests/test_tickets_cmd_evidence.py::TestKindGate::test_bug_kind_ticket_cannot_close_on_cmd_evidence_alone
- tests/test_tickets_cmd_evidence.py::TestKindGate::test_feature_kind_ticket_rejected
- tests/test_tickets_cmd_evidence.py::TestKindGate::test_security_kind_ticket_rejected
- tests/test_tickets_cmd_evidence.py::TestKindGate::test_docs_kind_closes
- tests/test_tickets_cmd_evidence.py::TestKindGate::test_docs_kind_ticket_failing_cmd_blocks_close
- tests/test_tickets_cmd_evidence.py::TestEvidenceCmdViaEvidenceSubcommand::test_records_cmd_evidence_on_docs_ticket
- tests/test_tickets_cmd_evidence.py::TestEvidenceCmdViaEvidenceSubcommand::test_requires_ids_or_cmd
- tests/test_tickets_cmd_evidence.py::TestCloseFromQueuedHint::test_close_on_queued_exits_nonzero
- tests/test_tickets_cmd_evidence.py::TestCloseFromQueuedHint::test_close_on_queued_hint_names_start
- tests/test_tickets_cmd_evidence.py::TestMissingEvidenceHint::test_missing_evidence_hint_names_tickets_md
- tests/test_tickets_cmd_evidence.py::TestStartOnInProgress::test_hints_at_sweep_and_exits_nonzero
- tests/system/test_cli_ticket.py::TestTicketRoundTrip::test_close_without_evidence_fails
- tests/test_tickets_cmd_evidence.py::TestIsCmdEvidence::test_shapes
- tests/test_tickets_cmd_evidence.py::TestCov003CmdEvidence::test_docs_ticket_closed_via_evidence_cmd_is_gate_clean
- tests/test_tickets_cmd_evidence.py::TestCov003CmdEvidence::test_bug_kind_ticket_with_hand_pasted_cmd_entry_fails_cov003
- tests/test_tickets_cmd_evidence.py::TestCov003CmdEvidence::test_docs_ticket_with_malformed_cmd_entry_fails_cov003
- tests/test_tickets_cmd_evidence.py::TestKindConsistencyAtClose::test_transition_refuses_close_when_kind_flipped_after_recording
- tests/test_tickets_cmd_evidence.py::TestKindConsistencyAtClose::test_land_validate_closeable_refuses_hand_pasted_cmd_entry
- tests/test_tickets_cmd_evidence.py::TestKindConsistencyAtClose::test_land_validate_closeable_accepts_docs_cmd_entry
designated_repro_test: null
threat: null
component: null
---
Filed from sibling-repo pilot P2 (lograder/aprog-public/aprog-private, 2026-07-18). Pilot P2 (gap 10) + coordinator experience this session (T-0167/T-0185/T-0186 all needed drift-lock tests written solely to satisfy close): frob ticket close accepts only pytest node ids. Add a vetted evidence alternative for docs/design tickets -- e.g. --evidence-cmd 'command' whose exit 0 is recorded with its output digest, or gate-based evidence referencing a rule that must be absent/present -- WITHOUT weakening code tickets (kind-gated: only docs/design kinds may use it). Also: close on a queued ticket errors InvalidTransition with no hint -- name the remedy (frob ticket start) in the message. And frob ticket start on an in-progress ticket errors InvalidTransition too -- make it idempotent or hint that it is already started (coordinator hit this on T-0169).