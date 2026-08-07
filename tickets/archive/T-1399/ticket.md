---
id: T-1399
title: 'Evidence binding does not verify the criterion: land closed T-1276 against
  116 live TEST005 findings'
state: done
kind: bug
origin: human
created: '2026-08-01'
priority: critical
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_evidence.py
- src/frob/tickets/_models.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_models.py
  reason: 'The gate-claim guard needs a new TicketError variant (GateClaimUnverified)
    distinct from AcceptanceUnbound (that one means no evidence at all is bound; this
    one means evidence is bound but does not establish the specific rule-id+glob outcome
    the criterion asserts). TicketError lives in src/frob/tickets/_models.py, not
    _evidence.py -- same split T-1384 used for OwnObligationsUnclean. Only the enum
    member plus its docstring line are added there; all detection/guard logic stays
    in _evidence.py.

    '
  actor: logan
  at: '2026-08-01'
evidence:
- tests/test_tickets_gate_claim_evidence.py::TestT1399GateClaimOnClose::test_transition_rejects_t1276_shape_when_gate_claims_verified_false
- tests/test_tickets_gate_claim_evidence.py::TestT1399GateClaimOnClose::test_transition_allows_t1276_shape_when_gate_claims_verified_true
- tests/test_tickets_gate_claim_evidence.py::TestT1399GateClaimOnClose::test_transition_permissive_when_gate_claims_verified_none
- tests/test_tickets_gate_claim_evidence.py::TestT1399GateClaimOnClose::test_transition_unaffected_when_no_gate_claim_criterion_exists
- tests/test_tickets_gate_claim_evidence.py::TestCriterionGateClaimDetection::test_t1276_shaped_criterion_matches
- tests/test_tickets_gate_claim_evidence.py::TestCriterionGateClaimDetection::test_ordinary_criterion_does_not_match
- tests/test_tickets_gate_claim_evidence.py::TestCriterionGateClaimDetection::test_gate_claim_criteria_filters_ticket_acceptance
designated_repro_test: null
acceptance:
- text: GIVEN an acceptance criterion asserting a package-wide gate outcome (0 TEST005
    findings under src/frob/app/**) WHEN evidence is bound that does not establish
    that outcome THEN close and land refuse rather than treating the criterion as
    satisfied
  evidence:
  - tests/test_tickets_gate_claim_evidence.py::TestT1399GateClaimOnClose::test_transition_rejects_t1276_shape_when_gate_claims_verified_false
  - tests/test_tickets_gate_claim_evidence.py::TestT1399GateClaimOnClose::test_transition_allows_t1276_shape_when_gate_claims_verified_true
  - tests/test_tickets_gate_claim_evidence.py::TestT1399GateClaimOnClose::test_transition_permissive_when_gate_claims_verified_none
  - tests/test_tickets_gate_claim_evidence.py::TestT1399GateClaimOnClose::test_transition_unaffected_when_no_gate_claim_criterion_exists
  - tests/test_tickets_gate_claim_evidence.py::TestCriterionGateClaimDetection::test_t1276_shaped_criterion_matches
  - tests/test_tickets_gate_claim_evidence.py::TestCriterionGateClaimDetection::test_ordinary_criterion_does_not_match
  - tests/test_tickets_gate_claim_evidence.py::TestCriterionGateClaimDetection::test_gate_claim_criteria_filters_ticket_acceptance
- text: GIVEN the same criterion WHEN the named gate is actually run and reports zero
    findings THEN the close is permitted
  evidence:
  - tests/test_tickets_gate_claim_evidence.py::TestT1399GateClaimOnClose::test_transition_rejects_t1276_shape_when_gate_claims_verified_false
  - tests/test_tickets_gate_claim_evidence.py::TestT1399GateClaimOnClose::test_transition_allows_t1276_shape_when_gate_claims_verified_true
  - tests/test_tickets_gate_claim_evidence.py::TestT1399GateClaimOnClose::test_transition_permissive_when_gate_claims_verified_none
  - tests/test_tickets_gate_claim_evidence.py::TestT1399GateClaimOnClose::test_transition_unaffected_when_no_gate_claim_criterion_exists
  - tests/test_tickets_gate_claim_evidence.py::TestCriterionGateClaimDetection::test_t1276_shaped_criterion_matches
  - tests/test_tickets_gate_claim_evidence.py::TestCriterionGateClaimDetection::test_ordinary_criterion_does_not_match
  - tests/test_tickets_gate_claim_evidence.py::TestCriterionGateClaimDetection::test_gate_claim_criteria_filters_ticket_acceptance
threat: null
component: null
---
Measured on main 2026-08-01, immediately after landing T-1276.

T-1276's criterion [0] reads: "GIVEN the app package at the 75%/70% floors WHEN frob check --only test runs THEN it reports 0 TEST005 findings under src/frob/app/**".

frob check on main reports 116 TEST005 findings under src/frob/app/. The criterion is provably false. Yet T-1276 is now state=done on main, with LAND-PROOF verified=True.

How it passed: criterion [0] is "bound" to pytest node ids from tests/unit/test_doctor_runner_t1276.py. Those tests pass, so the binding is formally valid -- but they establish only that a few app tests exist, not that the package is at zero findings. Binding is positional: attaching ANY passing node id to a criterion marks it satisfied. Nothing checks that the evidence actually establishes what the criterion asserts.

The implementing agent explicitly did NOT close this ticket. It left T-1276 in-progress and said so in its report, precisely because the criterion was unmet. The land verb closed it anyway. So the guard was defeated over an agent's correct objection -- the human-facing convention (leave it open) and the tool behaviour (close it) disagree, and the tool wins silently.

Why critical: this is the false-close class this queue has repeatedly paid for, and it is now demonstrated reachable through the sanctioned land path with no override flag and no warning. Every "zero findings under package X" criterion in the queue is closeable this way -- that shape covers T-1279, T-1281, T-1294, T-1296, T-1305, T-1307, T-1309, T-1310, T-1350, T-1396 and more. T-1384 added an own-obligations check at close; it does not catch this, because the obligations ARE clean. It is the criterion's semantics that go unverified.

Two defensible fixes, not mutually exclusive:

1. Criteria that name a gate outcome should be discharged by RUNNING that gate, not by binding test node ids -- an evidence channel analogous to the docs-kind evidence-cmd but available to code-kind tickets, recording the gate's exit status and finding count.

2. Land should re-evaluate any criterion naming a rule id plus a path glob against the post-merge gate state and refuse on mismatch. That is the same shape as the existing ClaimDivergence check, which already does exactly this for the Done report's captured claims -- so the machinery exists and simply is not applied to acceptance criteria.

Related: T-1398 (the TEST005 per-symbol join defect) means an unknown share of those 116 findings are themselves artifacts. Both must be fixed. A correct number that can still be falsely certified is no better than a wrong one.

Immediate remediation owed regardless of the fix chosen: T-1276 is done-on-main against an unmet criterion and cannot be requeued (only in-progress tickets can). Its honest remainder -- roughly 50 unsampled app runner entrypoints -- needs a successor ticket so the work is not lost to the false close.