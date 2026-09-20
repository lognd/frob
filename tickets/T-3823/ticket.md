---
id: T-3823
title: 'F-018: docs/strata secret grammar vs charter prose mismatch (rotate within/revoke
  via ... within reads like syntax but impl is issued_by/lifetime/revoke; no way to
  name the revocation FLOW) -- reconcile grammar and prose'
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
- strata-core/src/parse/grammar_policy.rs
- design/litmus/secret_lifecycle.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: strata-core/src/parse/grammar_policy.rs
  reason: '2026-09-19: converted to an implementation leaf -- the parser must accept
    the documented secret rotate-within/revoke forms, proven by its own new litmus
    file; grammar_node.rs is deliberately excluded because T-3822 holds it'
  actor: logan
  at: '2026-09-19'
- op: add
  glob: design/litmus/secret_lifecycle.strata
  reason: '2026-09-19: converted to an implementation leaf -- the parser must accept
    the documented secret rotate-within/revoke forms, proven by its own new litmus
    file; grammar_node.rs is deliberately excluded because T-3822 holds it'
  actor: logan
  at: '2026-09-19'
triage_changes:
- field: parent
  old_value: null
  new_value: T-4667
  reason: '2026-09-19: SF-22 in the STRATA friction audit; joins story D (DECISIONS)
    of epic T-4662 alongside T-3822 -- same docs-vs-parser class at statement level'
  actor: logan
  at: '2026-09-19'
- field: parent
  old_value: T-4667
  new_value: T-4665
  reason: '2026-09-19: owner decided the parser is incomplete rather than the prose
    wrong, converting this from a DECISION into implementation work; it moves from
    story D (T-4667) to story B (T-4665)'
  actor: logan
  at: '2026-09-19'
- field: kind
  old_value: bug
  new_value: feature
  reason: '2026-09-19: converted from a docs decision into implementation work on
    the parser (owner decision: the parser is incomplete, not the prose wrong)'
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
- mode: append
  reason: '2026-09-19: owner decision recorded -- the PARSER is incomplete, not the
    prose wrong; this converts from a DECISION into an implementation leaf under story
    B (T-4665), acceptance becomes ''the documented form parses and elaborates with
    a litmus case'''
  actor: logan
  at: '2026-09-19'
  old_length: 1548
  new_length: 4432
designated_repro_test: null
acceptance:
- text: Given docs/strata's secret grammar and the charter prose describe 'rotate
    within ...' and 'revoke via ...' forms that strata-core's parser does not accept,
    and the owner decided the PARSER is incomplete rather than the prose wrong, when
    this lands, then the documented forms PARSE and ELABORATE, proven by design/litmus/secret_lifecycle.strata
    -- a litmus case that fails to parse at HEAD c8f56ef10 and passes after.
  evidence: []
- text: Given this ticket's finding is that there is no way to NAME the revocation
    flow, when this lands, then a revocation flow can be named in the model and the
    elaborator reports it, exercised by the same litmus case.
  evidence: []
- text: Given revoke, within, lifetime and issued_by already appear in the lexer but
    only inside design/litmus fixtures (SF-09), when this ticket starts, then what
    actually parses today is established first and recorded, since the keyword list
    is only a lower bound on what the grammar reaches.
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


## DECISION RECORDED -- owner, 2026-09-19 19:50 -- NOW AN IMPLEMENTATION LEAF

**Decided: the PARSER IS INCOMPLETE. The prose is not wrong. Make the documented
secret lifecycle forms (`rotate within ...`, `revoke via ...`) parse and
elaborate, and give the revocation FLOW a way to be named.**

Governing posture, in the owner's words: **"err on the side of adding
capabilities; we originally had a good idea and then forgot to implement it."**
This ticket's own finding said the charter prose "reads like syntax but impl is
issued_by/lifetime/revoke" and that there is "no way to name the revocation
FLOW". Under the decision that is not a documentation defect to be written down
more carefully -- it is a designed capability that was never built.

This reverses this ticket's ORIGINAL framing. Its title still says "reconcile
grammar and prose", which reads as though either side could move. **Only the
parser moves.** Read the title as the finding, not the remedy.

CONVERTED FROM DECISION TO IMPLEMENTATION LEAF. Re-parented from story D
(T-4667, decisions) to **story B (T-4665)**. Acceptance is replaced with: the
documented forms parse AND elaborate, proven by a litmus case.

CORROBORATING MEASUREMENT (SF-09): `revoke` and `within` are both in the list of
19 keywords that appear ONLY in design/litmus fixtures and never in a real
model, and `lifetime` and `issued_by` are in that same list. So the lexer
already knows these words and the litmus corpus is the only thing keeping them
alive -- which is consistent with "designed, half-built, then forgotten", and is
why the deliverable here is a litmus case rather than only a unit test. Per
SF-09's own boundary note, presence in the keyword list is a LOWER bound on what
the grammar reaches, so establish what actually parses today before writing the
fix.

SCOPE AND DISJOINTNESS
- `strata-core/src/parse/grammar_policy.rs` and `strata-core/src/parse/mod.rs`
  -- confirmed by `git grep -ln '"secret"|"rotate"|"revoke"|"issued_by"|"lifetime"'
  -- strata-core/src/parse/`, which ALSO names `grammar_node.rs`.
- <!-- frob:waive DOC006 reason="illustrative target path for the litmus file this ticket creates -- does not exist until this ticket lands" -->`design/litmus/secret_lifecycle.strata` -- a NEW litmus file, deliberately its
  own file so this leaf stays scope-disjoint from T-3822.
- **HARD SEQUENCING NOTE:** `grammar_node.rs` is T-3822's declared scope and is
  deliberately NOT in this ticket's scope. If the secret lifecycle grammar
  proves to live there, these two leaves are SEQUENCED, not parallel: coordinate
  with T-3822 and `frob ticket scope --add` only after it lands, rather than
  racing the lease. Per memory/leases-and-scope.md the lease file is the truth.

WHY A LITMUS CASE: a documented form with no litmus case is how a construct
becomes dead again -- SF-09 measured 19 constructs alive only because litmus
exercises them. Per memory/positive-control-or-it-proves-nothing.md the litmus
case must fail to parse at HEAD and pass after.
