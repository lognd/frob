---
id: T-3823
title: 'F-018: docs/strata secret grammar vs charter prose mismatch (rotate within/revoke
  via ... within reads like syntax but impl is issued_by/lifetime/revoke; no way to
  name the revocation FLOW) -- reconcile grammar and prose'
state: queued
kind: bug
origin: human
created: '2026-09-05'
priority: medium
parent: T-4667
tier: ticket
sprint: v1.1.0
runs_last: false
milestone: v1.1.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: parent
  old_value: null
  new_value: T-4667
  reason: '2026-09-19: SF-22 in the STRATA friction audit; joins story D (DECISIONS)
    of epic T-4662 alongside T-3822 -- same docs-vs-parser class at statement level'
  actor: logan
  at: '2026-09-19'
body_changes:
- mode: append
  reason: '2026-09-19: attaching SF-22''s evidence row verbatim plus the SF-09 corroboration
    that both revoke and within are implemented in the parser but appear ONLY in litmus
    fixtures, which makes this more likely prose-vs-surface than a missing feature'
  actor: logan
  at: '2026-09-19'
  old_length: 0
  new_length: 1548
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## SF-22 evidence (attached 2026-09-19 by the STRATA friction epic, T-4662)

Recorded in scratchpad/STRATA-FRICTION.md as SF-22, evidence table row verbatim:

| SF-22 | Documented-vs-implemented grammar mismatches are ticketed but open | T-3822 (attr IDENT form: surface.md/threat.md vs parser), T-3823 (secret `rotate within`/`revoke` prose vs grammar) | 2 | LOW |

And verbatim from the SF-21/22/23 section:
"T-3823 (F-018): 'docs/strata secret grammar vs charter prose mismatch (rotate
within/revoke ...)'. Both queued."

Corroborating measurement from SF-09: both `revoke` and `within` are in the list
of 19 keywords that appear ONLY IN LITMUS FIXTURES and never in a real model.
So the constructs this ticket's prose describes are implemented in the parser and
exercised only by design/litmus/*.strata. That is the same discoverability shape
SF-09 found for `confine` -- documented, implemented, unused -- and it means the
mismatch here is more likely to be prose-vs-surface than a missing feature.

NOW A CHILD OF T-4667 (story D of epic T-4662), as a DECISION and not as a doc
fix, for the same reason as T-3822: "the prose is wrong" and "the grammar is
incomplete" are both consistent with the evidence, and choosing between them is
a statement about what the language should accept -- which the owner is
personally rethinking.

Decide it together with T-3822 (same class, node grammar), T-4681 (DECISION:
SF-21, same class at framing level) and T-4678 (DECISION: SF-09, which produces
the keyword-to-surface table this answer depends on).
