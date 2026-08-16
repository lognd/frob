---
id: T-1614
title: 'RUNS LAST: audit every frob:waive for cop-outs, after all other work is complete'
state: queued
kind: security
origin: human
created: '2026-08-05'
priority: high
blocked_by:
- T-1612
- T-1611
- T-1613
parent: T-1609
tier: ticket
sprint: null
runs_last: true
scope:
- src/frob/**
- tests/**
- docs/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
Audit every frob:waive directive in the repository and confirm each is a genuine, still-necessary exception rather than a cop-out.

THIS TICKET RUNS LAST. Not last among the tickets that existed when it was filed -- last, absolutely. Tickets filed after this one also precede it. The blocked_by edges recorded here cover only what existed at filing time and are therefore a floor, never the whole precondition.

STANDING PRECONDITION, to re-check immediately before starting: every other ticket in the queue is done, dropped, or archived. If `frob ticket list --state queued` or `--state in-progress` returns ANYTHING other than this ticket, it is not yet time -- stop and work that instead. See the runs-last enforcement ticket for making this mechanical rather than a promise.

Why last: a waiver's honesty can only be judged against finished code. Many waivers name a follow_up ticket, and judging them before that work lands would condemn waivers doing exactly what they promised. A waiver audit run early produces confidently wrong answers -- it would delete honest waivers and bless ones whose justification has not yet expired.

For every waiver, decide one of:
- STILL NECESSARY AND HONEST -- the reason describes a real constraint that still holds. Keep. Confirm the reason explains WHY rather than restating the rule.
- OBSOLETE -- the condition passed, the code changed, or the follow-up landed. Remove the waiver and let the gate speak.
- A COP-OUT -- it exists because fixing the finding was inconvenient. Remove it and fix the underlying finding, or, if the fix is genuinely large, replace it with a real ticket and a waiver naming that ticket.
- PERMANENT BY DESIGN -- no follow-up will ever exist (a private test helper with no production caller is the canonical case). These need a way to say so; the permanent-waiver ticket already filed covers that gap.

Specific things this drive learned to look for:
- A reason that merely restates the rule name is not a justification.
- A follow_up pointing at a done ticket is an orphan, not a waiver.
- Waivers added in bulk during a burn-down deserve extra scrutiny: cop-outs cluster there.
- A waiver on a rule that structurally cannot fire (a diff-scoped rule judged on a full run) is noise, not an exception, and belongs in that rule's exemption list instead.

Deliverable: every waiver classified, obsolete and cop-out waivers removed, and a count reported by category. A waiver left unexamined defeats the exercise.