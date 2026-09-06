---
id: T-4037
title: 'rule-shaped finding kind: done-condition is rule loaded, not instances fixed'
state: queued
kind: invariant
origin: agent
created: '2026-09-06'
priority: critical
parent: T-4036
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_models.py
- src/frob/app/ticket_runner/_close_cmd.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given the design step, when it completes, then it names the finding-kind mechanism
    (new TicketKind vs orthogonal flag), the machine-verifiable done-condition check
    (registry read vs frob check --only invocation), and whether the check runs at
    close only or close and land
  evidence: []
- text: given the design is accepted, when a rule-shaped ticket cites only instance-fix
    evidence with the named rule id absent from the loaded gate/policy registry, then
    close is refused, not merely warned
  evidence: []
- text: given the 35 children already filed across T-3919/T-3920/T-3928/T-3942/T-3984/T-4025,
    when this ticket's design step completes, then it lists which of them are rule-shaped
    and require this constraint applied retroactively
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Item 1, FILED FIRST as instructed -- this is not one item among nine, it is the mechanism that protects the 35 children already filed across T-3919/T-3920/T-3928/T-3942/T-3984/T-4025. VERIFIED: TicketKind (src/frob/tickets/_models.py, currently FEATURE/BUG/SECURITY/UX/DOCS/INVARIANT/INCIDENT) has no kind whose close-condition is "a rule exists and is loaded" rather than "the cited pytest/cmd evidence passed" -- every existing kind closes on evidence ABOUT THE CODE, never on evidence about the GATE CONFIGURATION itself. CMD_EVIDENCE_ALLOWED_KINDS (DOCS, UX) is the closest existing precedent for a non-pytest close condition, and it is the right shape to extend from, not duplicate.

THE CONSUMER'S EVIDENCE, worth preserving in full: the checked_mul policy rule asked for by their 2026-09-05 audit was never shipped. The named sites were hand-fixed instead (T-0157/T-0180 in their tracking). Four SIBLING sites in the same crate still carry the identical bug -- two of them TEN LINES from a sibling that carries the fix AND a nine-line comment explaining it. Hand-fixing did not even propagate within one file, let alone across the crate. Their conclusion, exact: "an audit finding whose remediation is a policy rule must not be closable by fixing the instances."

WHY THIS IS URGENT NOW, not merely a good idea: T-3942 was filed BECAUSE three first-audit rule-shaped asks were never built and their defects recurred. This drive's response was to decompose five more audit epics into 35 children, nearly all of them new-rule asks (ASSERT001, RACE001, PROTO001, TAINT-IDENT001, and so on). If ANY of those 35 can be marked done by an implementer who hand-fixes the cited instances rather than shipping and loading the rule, this drive reproduces T-3942's exact failure at 35x scale, with the queue itself reporting green the whole time.

DESIGN, to be completed before implementation (this ticket's own first step), covering at minimum:

1. THE FINDING/TICKET KIND. Either a new TicketKind (e.g. RULE, or a `--rule-shaped` flag/field orthogonal to the existing kind enum, since a rule-shaped remediation can be a SECURITY or BUG kind ticket that additionally carries this constraint) -- decide which, and justify against TicketKind's existing shape (kind currently also drives CLI-wiring grants and CMD_EVIDENCE_ALLOWED_KINDS; a new kind interacts with both).

2. THE DONE-CONDITION, MACHINE-VERIFIED. `frob check --only policy` (or the equivalent for a gate-registry rule rather than a policy.pattern one -- generalize past policy.pattern specifically, since most of the 35 children are gate rules, not policy patterns) must LIST the rule id as loaded before the ticket can close. Design how this is checked: does `frob ticket close` invoke `frob check --only <stage>` itself and grep the rule id out of the result, or does it read the gate registry (frob.gates._ALL_GATES / frob.gates._waive._KNOWN_GATE_RULES, the authoritative source T-3844's own done report names) for the rule id directly? Prefer the registry read -- it does not require the rule to actually FIRE (a rule can be loaded and correctly find zero live violations), only to EXIST and be wired into the active gate/policy set.

3. INTERACTION WITH close/land. A rule-shaped ticket citing pytest/cmd evidence for the FIXED INSTANCES ALONE, with no rule loaded, must be REFUSED at close (not merely warned) -- mirroring how a no-exit waiver or a missing designated_repro_test already hard-refuses today. Decide whether this check also runs at land time (defense in depth, matching how other ticket-shape guards run at both close and land) or only at close.

4. RETROACTIVE APPLICATION TO THE 35 CHILDREN ALREADY FILED. This ticket's design step must explicitly walk the 35 children from T-3919/T-3920/T-3928/T-3942/T-3984/T-4025 and flag which ones are rule-shaped (nearly all of the RULE-ID-named ones: ASSERT001, RACE001, PROTO001, TAINT-IDENT001, POL000, TESTRUN001, INV000, SEV001, TESTMOCK001, and more) so they get this constraint applied retroactively rather than only to tickets filed after this one lands -- otherwise the fix protects only future work, not the population it was raised specifically to protect.
