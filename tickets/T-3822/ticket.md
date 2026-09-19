---
id: T-3822
title: 'F-017: docs/strata/surface.md + threat.md node grammar shows attr IDENT form
  but the real form needs STRING (attr "privacy-policy"; retention=90d) -- fix the
  docs to show the STRING attr form'
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
    of epic T-4662 -- docs-vs-parser disagreement is a question about which artifact
    is the specification, which the owner is rethinking'
  actor: logan
  at: '2026-09-19'
body_changes:
- mode: append
  reason: '2026-09-19: attaching SF-22''s evidence row verbatim and recording that
    this is one of four scales of the same question (with T-3823, T-4681/SF-21 and
    T-4678/SF-09), to be decided together'
  actor: logan
  at: '2026-09-19'
  old_length: 0
  new_length: 1398
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
"T-3822 (F-017): 'docs/strata/surface.md + threat.md node grammar shows attr
IDENT form' that the parser does not accept."

NOW A CHILD OF T-4667 (story D of epic T-4662), as a DECISION and not as a doc
fix. The reason is that "the docs are wrong" and "the parser is missing a form"
are both consistent with the evidence, and choosing between them is a statement
about what the language should accept -- which is precisely what the owner is
personally rethinking. Writing either answer down now would pre-empt that.

Decide it together with:
- T-3823 (F-018), the same class at statement level for the secret grammar;
- T-4681 (DECISION: SF-21), the same class at framing level -- kernel.md says
  "six primitives" while the parser accepts 139 keywords;
- T-4678 (DECISION: SF-09), which must produce a keyword-to-surface table that
  this ticket's answer depends on.

All four are one question asked at four scales: when the docs and the parser
disagree, which one is the specification?
