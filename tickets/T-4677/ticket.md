---
id: T-4677
title: 'DECISION: SF-08 -- 33/33 assumes are one boilerplate shape, one owner, one
  date; how should a weakness class be stated once?'
state: in-progress
kind: docs
origin: agent
created: '2026-09-19'
priority: high
parent: T-4667
tier: ticket
sprint: v0.536.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: true
no_scope_declared_reason: '2026-09-19: DECISION ticket -- its deliverable is an owner
  decision recorded in the body, which legitimately changes no files'
body_changes:
- mode: append
  reason: '2026-09-19: owner DECISION D-M8 recorded; this decision ticket''s deliverable
    is complete and it closes with no behavior change'
  actor: logan
  at: '2026-09-19'
  old_length: 3431
  new_length: 5448
- mode: append
  reason: 'BUG002 front door (T-2393): 2026-09-19: DECISION ticket whose sole deliverable
    is an owner decision recorded in the body. Owner recorded D-M8 (assumes are module-owned
    and specific; a structural gate refuses templated assumes), which rejects the
    framing of all three options this ticket offered. Implementation belongs to the
    module-system story, not here. No code, model or doc file changes under this id.'
  actor: logan
  at: '2026-09-19'
  old_length: 5448
  new_length: 5861
- mode: append
  reason: 'BUG002 front door (T-2393): 2026-09-19: DECISION ticket whose sole deliverable
    is an owner decision recorded in the body. Owner recorded D-M8 (assumes are module-owned
    and specific; a structural gate refuses templated assumes), which rejects the
    framing of all three options this ticket offered. Implementation belongs to the
    module-system story, not here. No code, model or doc file changes under this id.'
  actor: logan
  at: '2026-09-19'
  old_length: 5861
  new_length: 6274
designated_repro_test: null
acceptance:
- text: 'Owner records a decision in the body: which of the three options (class-level/quantified
    assume, defaults-and-inheritance, or generated boilerplate), and what it changes.
    No implementation ticket may be filed against SF-08 before that decision is recorded.'
  evidence: []
threat: null
component: strata
anchor: false
anchor_reason: null
land_commit: null
---
DECISION TICKET. SF-08 (MEDIUM). Child of story D (T-4667) under epic T-4662.
NOT implementation work. Do not build anything until the owner records a
decision in this body.

EVIDENCE TABLE ROW, VERBATIM FROM scratchpad/STRATA-FRICTION.md:
| SF-08 | 100% of assumes are one boilerplate shape, one per node per CWE, with an identical owner and identical date | design/frob.strata:1875,1887,2472,2489,2506,2519,2535,2551...: `assume "weakness:CWE-78:<node>" noflow registry -> <node> owner logan review "2026-10-15"` x18 CWE-78, 6 CWE-94, 3 CWE-89, 2 each CWE-502/639/918 | 33/33 | MEDIUM |

FULL EVIDENCE (SF-08 section, verbatim):
All 33 `assume` statements in design/frob.strata match
`assume "weakness:CWE-NNN:<node>" noflow registry -> <node> owner logan review "2026-10-15"`.
Breakdown: CWE-78 x18, CWE-94 x6, CWE-89 x3, CWE-502 x2, CWE-639 x2, CWE-918 x2.
One owner (`logan`), one date (`2026-10-15`) for all 33. Zero assumes of any
other shape -- there is no `bound`, `reach`, `frame` or set-equality assume
anywhere in the file, though the kernel defines all of them
(docs/strata/kernel.md:46-62).

That is (nodes x weaknesses) growth: every new node registered under SYS102 will
need 6 more assume lines of identical text.

A fix would have to change: the grammar/semantics (a way to say "this weakness
class does not reach any trusted node" once), not the gate.

OPTIONS THE EVIDENCE SUPPORTS

Option 1 -- a class-level / quantified assume.
One statement asserting a weakness class does not reach any node of a given kind,
instead of one statement per (node, CWE) pair. Would have to change: the grammar
(a quantifier or set form over the node universe), the elaborator (expanding or
evaluating it without materialising 33+ claims), and the assumption ledger's
identity scheme, since claim ids today embed the node name
("weakness:CWE-78:<node>") and reports, waivers and review dates all key off
that id. Cost: the ledger loses per-node granularity unless ids are synthesised.

Option 2 -- defaults and inheritance at the registry/node level.
Keep the per-node claim identity but let a node or registry declare its weakness
posture once and inherit. Would have to change: the grammar (a defaults block),
and the elaborator's claim synthesis. Shares its machinery with SF-10's
duplication problem, so deciding these two together is cheaper than separately.

Option 3 -- no grammar change; treat the boilerplate as generated.
Accept the 33 lines as machine-written output of a generator that takes the node
list and the CWE list. Would have to change: tooling only, plus a gate that the
generated block is in sync. Cost: design/frob.strata stops being hand-authored
in that region, and the whole-file lease problem (T-4598) gets worse, not better,
because a generator rewrites the region on every node addition.

INTERACTIONS THE OWNER SHOULD WEIGH
- The shared date is SF-07's cliff: 33 claims expiring on 2026-10-15 is a
  fleet-wide event. Options 1 and 2 make the date a single edit; option 3 makes
  it a generator input. Leaf C1 (T-4666's child) wires the overdue verdict
  regardless of which is chosen.
- SF-09 records that `frame` is among the 56 keywords used NOWHERE, while
  kernel.md:46-62 defines bound/reach/frame assumes. Some of the expressiveness
  this decision wants may already be implemented and merely unreachable.

ACCEPTANCE
Owner records a decision in the body: which option, and what it changes.


## DECISION RECORDED -- owner, 2026-09-19 (D-M8)

**Decided: none of the three options as framed. Assumes become MODULE-OWNED and
SPECIFIC, and a structural gate REFUSES templated assumes.**

D-M8, from the owner's module-system decisions: an assume belongs to the module
whose weakness it is about, and it must say something specific about that module.
The 33-line `assume "weakness:CWE-NNN:<node>" noflow registry -> <node> owner
logan review "2026-10-15"` block measured in SF-08 is exactly the shape the new
gate refuses -- it is one template instantiated per node, asserting nothing a
reader could not derive from the node list.

This rejects the framing of all three options this ticket offered:
- Option 1 (class-level/quantified assume) would make the templating CHEAPER to
  express. The decision makes it illegal instead.
- Option 2 (defaults/inheritance) is superseded by module ownership: the unit
  that carries the posture is the module, not a defaults block.
- Option 3 (generated boilerplate) is the exact opposite of the decision -- a
  generator is a machine for producing templated assumes at scale.

Consequences for whoever implements it, in the module-system story being filed
by the other planner (this ticket does NOT own that work):
- a structural gate that refuses a templated assume -- i.e. detects N assumes
  differing only by a node name substitution -- and the 33 existing ones must be
  rewritten as specific, module-owned claims or removed;
- the shared `review "2026-10-15"` date stops being a fleet-wide cliff once
  assumes are module-owned, because each module reviews on its own cadence;
- T-4675 (SF-07, wiring the overdue-assume verdict) is UNAFFECTED and still
  lands independently -- it makes an overdue review a gate failure regardless of
  who owns the assume, and it is the CRITICAL leaf with 26 days to 2026-10-15.

Closing with no behavior change: the deliverable of a DECISION ticket is the
decision, now recorded above. No code or model file changes under this id.


frob:no-behavior-change reason="2026-09-19: DECISION ticket whose sole deliverable is an owner decision recorded in the body. Owner recorded D-M8 (assumes are module-owned and specific; a structural gate refuses templated assumes), which rejects the framing of all three options this ticket offered. Implementation belongs to the module-system story, not here. No code, model or doc file changes under this id."

frob:no-behavior-change reason="2026-09-19: DECISION ticket whose sole deliverable is an owner decision recorded in the body. Owner recorded D-M8 (assumes are module-owned and specific; a structural gate refuses templated assumes), which rejects the framing of all three options this ticket offered. Implementation belongs to the module-system story, not here. No code, model or doc file changes under this id."