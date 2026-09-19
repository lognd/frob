---
id: T-4677
title: 'DECISION: SF-08 -- 33/33 assumes are one boilerplate shape, one owner, one
  date; how should a weakness class be stated once?'
state: queued
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
