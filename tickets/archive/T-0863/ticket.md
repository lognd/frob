---
id: T-0863
title: fix T-0755 self-check regression from T-0844's uncovered ticket_runner/config
  lines
state: dropped
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner.py
- src/frob/app/config.py
- tests/test_tickets_mutation_evidence.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_self_check_t0755_own_diff_zero_error_findings now fails: it runs mutation_evidence_violations(repo_root, T-0755, "main") over the current diff, using T-0755 own bound evidence as the mutation-kill oracle, and T-0755 own declared scope includes src/frob/app/ticket_runner.py and src/frob/app/config.py. T-0844 (security-kind, closed) added new confirmatory-only lines to those two files: _close_mutation_evidence_for_ticket, _close_failure_hint EvidenceConfirmatoryOnly branch, and the ticket_close_skip_mutation_evidence field/flag wiring. T-0844 own verify command list (frob ticket brief T-0844) did not include tests/test_tickets_mutation_evidence.py, so this self-check regression went uncaught at T-0844 close time.

Remedy: either (1) add/strengthen an adversarial test bound as T-0755 evidence that actually kills a mutant of the new ticket_runner.py/config.py lines T-0844 introduced, or (2) if that is judged not worth doing for such small glue code, scope T-0755 evidence down / accept a documented exception for this self-check the way other pre-existing gate debt is waived elsewhere in this repo. Discovered while working T-0854 (own scope is src/frob/tickets/** + src/frob/gates/**, does not include ticket_runner.py/config.py, so this cannot be fixed inside T-0854 without scope creep back into a different, already-closed ticket's security-kind gate).

## Drop reason
- 2026-07-23: Fully resolved by T-0844 rework: new adversarial tests in tests/test_ticket_land.py (TestCloseSkipMutationEvidenceCliWiring, TestCloseMutationEvidenceForTicket, TestCloseFailureHintMutationEvidence, TestCloseSkipMutationEvidenceBypass) were bound as T-0755 evidence, covering the confirmatory-only lines this draft named in config.py/ticket_runner.py. test_self_check_t0755_own_diff_zero_error_findings now passes (verified by direct rerun). No residual gap.