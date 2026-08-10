---
id: T-1930
title: add a single porcelain verb sequencing the happy-path ticket workflow (T-1556
  criterion 2b)
state: dropped
kind: ux
origin: human
created: '2026-08-09'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/**
- src/frob/_cli_parsers/_ticket/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-1556's criterion 2 has two halves: (a) every close/land refusal names
the exact next command, and (b) a single porcelain verb exists that
sequences the happy path (start -> implement -> evidence -> accepts ->
done-report -> close). T-1556 delivered (a) in full (_close_cmd.py's
_close_failure_hint now covers EvidenceScopeUnbound, EvidenceNotPassing,
OwnObligationsUnclean, GateClaimUnverified, LiveTrackerCited, and
NewGateRuleUnaccepted, each naming the exact remedy command) but not (b)
-- no new porcelain verb was added. Filed as its own follow-up so it does
not silently get treated as delivered under T-1556's already-closed
acceptance trail.

## Drop reason
- 2026-08-10: Investigated per this ticket own invitation to argue for automatic-over-command if warranted -- concluding a new porcelain verb is the wrong shape here, not shipping it. T-1556 already delivered the half that generalizes: every close/land refusal (_close_failure_hint, EvidenceScopeUnbound/EvidenceNotPassing/OwnObligationsUnclean/GateClaimUnverified/LiveTrackerCited/NewGateRuleUnaccepted) names the exact next command at the point of failure, which is where an operator actually needs it, not in a workflow doc read once. This repo already automates every step of the happy path that needs NO judgment: frob ticket work absorbs worktree-create+merge+build+start into one call; start auto-plans a queued ticket and auto-commits the transition; land absorbs fmt, Tier-A auto-fixes, the pre-land baseline, and the post-land rebase, all without being asked. What remains in the (implement, evidence, accepts, done-report, close) chain is NOT sequencing -- it is judgment: which tests are real evidence for this specific defect, what the acceptance criteria actually are, what the done-report narrative honestly says happened. A wrapper verb around those steps would not remove any judgment call; it would just be a new command surface an agent has to separately learn exists, the exact failure mode the standing automatic-over-commands directive warns about (a command requires knowledge of the command). The better remaining investment, if there is unmet friction here, is tightening the SAME already-shipped hint mechanism (T-1556) at the specific steps this ticket felt were unsequenced, not adding a sequencing verb on top of it.
