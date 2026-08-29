---
id: T-3295
title: 'A waiver whose reason promises follow-up is debt, ticket or not: the discriminator
  already exists and WAIVE009 wires it to the wrong conclusion (2656 waive vs 124
  debt)'
state: queued
kind: feature
origin: human
created: '2026-08-28'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_waive.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
OWNER DIRECTIVE 2026-08-28: "I don't like how frob:waive is used when frob:debt
should be used; can we think of a way to ensure that waive is MEANT and not
debt?"

THE ANSWER IS THAT THE DISCRIMINATOR ALREADY EXISTS AND IS WIRED TO THE WRONG
CONCLUSION.

`src/frob/gates/_waive.py:1839`

    def _reason_promises_followup(reason: str) -> bool:
        """Whether `reason` reads as promising deferred/future work (a
        follow-up ticket, "once X clears", ...) ... independent of whether
        any ticket id actually backs the promise."""

WAIVE009 calls it and then asks only ONE question: does the reason name a
ticket id that resolves? If yes, the waiver passes.

So `frob:waive RULE reason="deferred, see T-1234"` is CLEAN today. But read what
it says. It asserts the rule DOES apply and the violation is REAL and UNFIXED.
That is the definition of debt. Naming a ticket makes the promise accountable;
it does not make the classification correct.

THE RULE THAT SHOULD HOLD, and it is decidable with the code already written:

    a waiver whose reason promises follow-up is a MISCLASSIFICATION,
    ticket or no ticket.

    frob:waive = this rule does not apply here, permanently and correctly.
                 There is nothing to fix. No future work is implied.
    frob:debt  = this rule DOES apply, the finding is real, it is not fixed
                 yet, and here is the ticket that will fix it.

If a reason needs to say when it will be fixed, it is debt. If it is a waiver,
there is no "when" -- that is the whole test, and `_reason_promises_followup`
already implements it.

CURRENT SCALE, measured 2026-08-28 across src/, tests/, docs/:

    frob:waive   2656
    frob:debt     124

That is 21:1. Measured earlier the same day it was 2192:93, a 24:1 ratio -- so
the absolute gap is GROWING while we work, not shrinking. Twenty-one waivers per
debt entry is not a codebase with 2656 rules that genuinely do not apply; it is
a codebase using the wrong directive because the wrong one passes.

WHY IT MATTERS BEYOND TIDINESS. A waiver is invisible to any accounting of
unfinished work. Debt is not -- it is the queue's own record that something is
owed. Every misclassified waiver is an obligation that has left the ledger while
looking accounted-for. The owner has repeatedly asked for unaccounted work to be
a build failure; this is the single largest channel through which it is not.

WHAT TO BUILD:
  1. A rule (new id in the WAIVE family, sibling to WAIVE009/010, reusing
     `_reason_promises_followup` verbatim -- do NOT write a second phrase
     detector) that flags a `frob:waive` whose reason promises follow-up,
     REGARDLESS of whether it cites a ticket. The remedy text must say
     "convert to frob:debt", not "add a ticket id".
  2. Decide and STATE what happens to WAIVE009. If every promise-shaped waiver
     becomes a misclassification finding, WAIVE009's "promise without a ticket"
     case is a strict subset. Either fold it in or say why both should exist --
     two rules for one condition is the desync bug this repo already knows.
  3. A migration path. 2656 waivers cannot be hand-audited. Measure how many
     actually trip `_reason_promises_followup` FIRST and report that number
     before designing the burn-down -- if it is 50, this is an afternoon; if it
     is 900, it needs a ratchet and a plan. Do not start converting before you
     have that count.

DO NOT SOLVE THIS BY MAKING THE NEW RULE A WARNING NOBODY ACTS ON. This repo
already carries WARN-tier gates it has not burned down. Propose the severity
with the measured count in hand, and propose a ratchet if the count is large --
a rule that fires 900 times on day one gets waived, which would be the joke
writing itself.

DO NOT WEAKEN THE PROMISE DETECTOR TO REDUCE THE COUNT. If
`_reason_promises_followup` has false positives, that is a separate finding to
report with examples, not a reason to loosen the test.

MUST-FIRE FIXTURE: `frob:waive RULE reason="deferred until T-1234 lands"` is
flagged as a misclassification even though T-1234 resolves.
MUST-STAY-QUIET FIXTURE: a genuine waiver -- a reason asserting the rule does
not apply, with no temporal or follow-up language -- is silent.
THIRD FIXTURE: an existing `frob:debt` citing a ticket is unaffected.

ACCEPTANCE
- The new rule reuses `_reason_promises_followup`; no second detector.
- A stated count of how many of the 2656 waivers trip it, measured before any
  conversion.
- A stated decision on WAIVE009's fate.
- A severity and (if needed) a ratchet proposed with that count in hand.
- All three fixtures present.
