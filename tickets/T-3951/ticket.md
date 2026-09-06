---
id: T-3951
title: 'F-188: COV002 demands per-symbol attribution the diff already implies (75
  symbols, two passes)'
state: queued
kind: ux
origin: human
created: '2026-09-06'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_fix_engine.py
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
Consumer logand.app-v2 F-188, 2026-09-06:

  "T-0170 touched about 75 symbols (private helpers and test functions included)
   and the agent had to annotate each one in two passes before COV002 passed. A
   ticket already owns its diff (scope + branch); COV002 should accept
   diff-level attribution (or frob:ticket at module level) and only demand
   per-symbol tags when a file is shared between tickets."

THE ARGUMENT IS STRONGER THAN IT LOOKS, so engage with it rather than dismissing
it as a request to weaken a gate. Their point is that the attribution COV002
demands is, in the common case, ALREADY DERIVABLE: the ticket owns a branch and a
scope, so every symbol in its diff is attributable without a single annotation.
The per-symbol tag carries new information only when a file is shared between
tickets -- which is exactly the case where it matters and exactly the case where
it is rare. So the current design pays the full annotation cost on every ticket
to buy information that is only needed on a few.

NOTE THE MEASURED COST: about 75 symbols, TWO passes. Private helpers and test
functions included. That is a substantial fraction of a session spent on
bookkeeping the system could have computed.

THIS IS THE THIRD REPORT OF ONE SHAPE. T-3939 (apollo: COV002 provenance edges
missed per ticket DESPITE EXPLICIT BRIEFS, "write-time enforcement would beat
land-time refusal") and T-3950 (F-189: the mutation gate surfaces only at
close/land) are the same complaint from different directions. Nobody disputes
the rules; they dispute WHEN and HOW MUCH MANUAL WORK the rules demand. Read all
three together -- if one mechanism serves them, build it once.

WHAT TO DETERMINE FIRST, and do not skip to the fix: what does COV002 actually
need the per-symbol edge FOR? If it is only "which ticket touched this symbol",
the diff plus the ticket's branch answers it and the annotation is redundant in
the unshared case. If it carries something the diff cannot express -- intent,
review granularity, or an edge other gates consume -- then diff-level attribution
LOSES information and the honest answer is to say so and reject the ask. Grep the
consumers of the edge before deciding. This repo's rule is that "X is redundant"
is a claim about code.

IF DIFF-LEVEL ATTRIBUTION IS SOUND, the consumer's own scoping is the right one:
derive attribution from the diff by default, and demand per-symbol tags only when
a file is genuinely shared between open tickets. That keeps the precision exactly
where it earns its cost.

BE CAREFUL OF THE OBVIOUS TRAP: a module-level frob:ticket that silently claims
symbols the ticket did not touch would be worse than the annotation burden -- it
would make attribution WRONG rather than tedious, and attribution is what other
gates build on. Whatever is derived must be derived from the actual diff, not
from a file-level assertion the user writes by hand.

MUST-FIRE FIXTURE: a symbol changed in a file SHARED by two open tickets still
demands explicit per-symbol attribution.
MUST-STAY-QUIET: a ticket touching many symbols in files it solely owns needs no
per-symbol annotation.
THIRD FIXTURE: derived attribution matches hand-annotated attribution on a
mixed case -- the equivalence, made checkable.

ACCEPTANCE
- What the per-symbol edge is consumed FOR, answered by grepping its consumers.
- Either diff-level derivation in the unshared case, or a stated reason it loses
  information.
- Cross-referenced with T-3939 and T-3950.
- All three fixtures committed.