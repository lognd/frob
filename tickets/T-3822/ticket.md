---
id: T-3822
title: 'F-017: docs/strata/surface.md + threat.md node grammar shows attr IDENT form
  but the real form needs STRING (attr "privacy-policy"; retention=90d) -- fix the
  docs to show the STRING attr form'
state: queued
kind: feature
origin: human
created: '2026-09-05'
priority: medium
parent: T-4665
tier: ticket
sprint: v1.1.0
runs_last: false
milestone: v1.1.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- strata-core/src/parse/grammar_node.rs
- design/litmus/attr_ident.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: strata-core/src/parse/grammar_node.rs
  reason: '2026-09-19: converted to an implementation leaf -- the parser must accept
    the documented attr IDENT form, proven by its own new litmus file (kept separate
    from T-3823''s so the two parser leaves stay scope-disjoint)'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: design/litmus/attr_ident.strata
  reason: '2026-09-19: converted to an implementation leaf -- the parser must accept
    the documented attr IDENT form, proven by its own new litmus file (kept separate
    from T-3823''s so the two parser leaves stay scope-disjoint)'
  actor: logan
  at: '2026-09-19'
triage_changes:
- field: parent
  old_value: null
  new_value: T-4667
  reason: '2026-09-19: SF-22 in the STRATA friction audit; joins story D (DECISIONS)
    of epic T-4662 -- docs-vs-parser disagreement is a question about which artifact
    is the specification, which the owner is rethinking'
  actor: logan
  at: '2026-09-19'
- field: parent
  old_value: T-4667
  new_value: T-4665
  reason: '2026-09-19: owner decided the parser is incomplete rather than the docs
    wrong, converting this from a DECISION into implementation work; it moves from
    story D (T-4667) to story B (T-4665)'
  actor: logan
  at: '2026-09-19'
- field: kind
  old_value: bug
  new_value: feature
  reason: '2026-09-19: converted from a docs decision into implementation work on
    the parser (owner decision: the parser is incomplete, not the docs wrong)'
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
- mode: append
  reason: '2026-09-19: owner decision recorded -- the PARSER is incomplete, not the
    docs wrong; this converts from a DECISION into an implementation leaf under story
    B (T-4665), acceptance becomes ''the documented form parses and elaborates with
    a litmus case'''
  actor: logan
  at: '2026-09-19'
  old_length: 1398
  new_length: 3835
designated_repro_test: null
acceptance:
- text: Given docs/strata/surface.md and docs/strata/threat.md document an 'attr IDENT'
    node form that strata-core's parser does not accept, and the owner decided the
    PARSER is incomplete rather than the docs wrong, when this lands, then the documented
    attr IDENT form PARSES and ELABORATES, proven by design/litmus/attr_ident.strata
    -- a litmus case that fails to parse at HEAD c8f56ef10 and passes after.
  evidence: []
- text: Given the existing STRING attr form is in live use across design/frob.strata
    (162 attr lines), when the IDENT form is added, then a test asserts the STRING
    form still parses and elaborates unchanged -- the negative control against fixing
    this by swapping one form for the other.
  evidence: []
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


## DECISION RECORDED -- owner, 2026-09-19 19:50 -- NOW AN IMPLEMENTATION LEAF

**Decided: the PARSER IS INCOMPLETE. The docs are not wrong. Make the documented
`attr IDENT` form parse and elaborate.**

Governing posture, in the owner's words: **"err on the side of adding
capabilities; we originally had a good idea and then forgot to implement it."**
docs/strata/surface.md and threat.md showing `attr IDENT` is exactly that shape:
the form was designed, written down, and never implemented. The fix is to
implement it, not to edit the documentation down to what the parser happens to
accept.

This reverses this ticket's ORIGINAL framing. Its title still reads "fix the
docs to show the STRING attr form" -- **that is now the rejected option**. Read
the title as the finding, not the remedy. The remedy is the opposite: the parser
gains the IDENT form, and the STRING form continues to work.

CONVERTED FROM DECISION TO IMPLEMENTATION LEAF. Re-parented from story D
(T-4667, decisions) to **story B (T-4665)**. Acceptance is replaced with: the
documented form parses AND elaborates, proven by a litmus case.

SCOPE AND DISJOINTNESS
- `strata-core/src/parse/grammar_node.rs` -- node `attr` parsing (confirmed by
  `git grep -ln '"attr"' -- strata-core/src/parse/`, which also names
  grammar_flow.rs and grammar_infra.rs; if the node attr form proves to live in
  one of those, scope --add it).
- <!-- frob:waive DOC006 reason="illustrative target path for the litmus file this ticket creates -- does not exist until this ticket lands" -->`design/litmus/attr_ident.strata` -- a NEW litmus file, deliberately its own
  file so this leaf stays scope-disjoint from T-3823, which also touches the
  parser.
- `docs/strata/surface.md`, `docs/strata/threat.md` -- these become CORRECT
  rather than aspirational once the parser accepts the form; check the examples
  against the implemented grammar and fix any that were wrong for a second
  reason.

SEQUENCING NOTE: T-3823 (the secret `rotate within`/`revoke` grammar) is the
same class and the same decision, and its parser site may also be
grammar_node.rs. If both leaves need that file, they are SEQUENCED, not
parallel -- coordinate rather than taking a lease race.

WHY A LITMUS CASE AND NOT ONLY A UNIT TEST: SF-09 measured that the 7
design/litmus/*.strata files are the ONLY thing exercising 19 constructs the
self-model never uses. A documented form with no litmus case is how a construct
becomes dead again. Per memory/positive-control-or-it-proves-nothing.md, the
litmus case must fail to parse at HEAD and pass after.
