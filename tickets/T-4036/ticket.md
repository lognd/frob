---
id: T-4036
title: 'F-240+: engine delta audit -- a rule-shaped remediation must not be closable
  by fixing instances'
state: queued
kind: security
origin: human
created: '2026-09-06'
priority: high
parent: null
tier: epic
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: true
no_scope_declared_reason: 'tier=epic: decomposition container for the seventh consumer
  audit list; scope lives on the children'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Consumer logand.app-v2, F-240 onward, verbatim from their
docs/security/audit-2026-09-06-engine-delta.md. SEVENTH audit list. Prior six:
T-3919, T-3920, T-3928, T-3942, T-3984, T-4025.

ITEM 1 IS THE HEADLINE AND IT IS ABOUT OUR PROCESS, NOT THEIR CODE:

  "The checked_mul policy rule asked for by the 2026-09-05 audit was never
   shipped, and the gap it named recurred immediately... instead T-0157/T-0180
   fixed the enumerated sites by hand. Four sibling sites in the same crate
   still carry the bug, two of them in a function whose sibling ten lines away
   carries the fix AND a nine-line comment explaining it. The lesson is not
   'write the rule next time' -- it is that AN AUDIT FINDING WHOSE REMEDIATION
   IS A POLICY RULE MUST NOT BE CLOSABLE BY FIXING THE INSTANCES. frob's ticket
   model needs a finding kind whose done-condition is 'a rule exists and is
   loaded', verifiable by `frob check --only policy` listing it, so a hand-fix
   cannot close it."

READ THAT AS A DIRECT WARNING ABOUT THE 35 CHILDREN WE JUST FILED. T-3942 exists
because three first-audit asks were never built and the defects recurred; we
responded by decomposing five epics into 35 dispatchable children. If those
children can be closed by fixing instances rather than shipping rules, we have
manufactured the same failure at larger scale. Their proposed mechanism -- a
done-condition of "the rule is loaded", machine-verifiable rather than
prose-asserted -- is the structural fix for that, and it is the single most
valuable item in this list. FILE IT FIRST.

The detail that makes their case is worth keeping: two of the four unfixed sites
sit ten lines from a sibling that carries the fix AND a nine-line comment
explaining it. Hand-fixing does not even propagate within one file.

ITEM 2 IS THE HIGHEST-VALUE NEW RULE KIND: unpaired resource acquisition. Three
of this pass's findings (performance.mark without clearMarks, Map.set with no
delete outside a test helper, setTimeout with no clearTimeout) are ONE missing
rule -- an acquire/release API pair where a scope contains the first without the
second. All structural AST shapes, no taint analysis, all invisible to every
existing gate, and it generalises to addEventListener/removeEventListener,
createObjectURL/revokeObjectURL and AbortController.

THE REST, in their order:
3  gate:DOC verifies pointer FRESHNESS, never CLAIM TRUTH -- four docstrings in
   this pass are false. They concede the general form is out of reach but
   propose a narrow rule for numeric literals in a docstring naming a buffer
   stride or size, which would have caught the same bug TWICE, eight ABI
   functions apart. Note this is the fourth arrival of docstring-claims-as-
   obligations (T-3919 item 4, T-3928's convergence 1, T-3942 item 6, now this);
   cross-reference T-3954 rather than filing a fifth.
4  A FILE include!'d RATHER THAN mod-DECLARED IS OUTSIDE EVERY GATE. Real code,
   two callers, doc comments, and gate:TEST/gate:DOC/gate:REF all report clean on
   a file none of them ever reads. THIS IS A SUBJECT-COUNT INSTANCE -- three
   gates reporting clean over a file absent from their subject set. Cross-
   reference T-3985; their fallback ask ("report an unwalked-but-tracked source
   file as a finding") is exactly that primitive applied to the walker.
5  Strata polices capability PRESENCE but not capability SCOPE: a decorative
   layer binding keydown on window is indistinguishable from a component
   listening on its own subtree, both being may "dom.event". Same shape as
   T-3990 and T-4025 item 4 -- strata's atoms are binary where the risk is in
   the argument. Third arrival of that shape; cross-reference, do not refile.
6  TWO FINDINGS ARE A STATE MACHINE WITH A STATE THAT HAS NO EXIT EDGE (a frame
   loop reaching STOPPED with no path back to RUNNING; input latches reaching
   HELD with no path back to RELEASED). Strata models nodes, flows and
   capabilities, not LIFECYCLES. They propose a thin state/transition construct:
   named states plus required edges, checked for reachability.
   A NOTE ON RESONANCE, DELIBERATELY NOT A MERGE: this queue tracks a "no-exit"
   class at ten instances (a rule demanding something the subject structurally
   cannot provide). That is a DIFFERENT population from a state machine lacking
   a transition -- shared abstraction, different subject and detector. Record the
   resonance if it helps design; do NOT cite our ten instances as evidence for
   this item. I made exactly that over-merge on T-4025 item 2 and a measurement
   refuted it.
7  A WAIVED frob:tests SHOULD STILL RECORD THE KIND IT CLAIMS. When a gate is
   waived for a TOOLING reason, the waiver says why the evidence is invisible but
   not what the evidence COVERS -- so nobody notices the tests are unit-shaped
   where the claim is integration-shaped. Note the waiver in question exists
   because of T-4016 (the TS walker emitting no symbol for it()), so this item is
   downstream of a defect we have already filed.

GUIDANCE, unchanged from the previous six: DO NOT BUILD ALL OF IT. Decompose,
keep the audit's ordering, name the finding each child would have caught, and
VERIFY EACH AGAINST WHAT EXISTS FIRST -- five items across the earlier epics
turned out already implemented.

ACCEPTANCE
- Item 1 filed FIRST, as a mechanism ensuring a rule-shaped remediation cannot
  be closed by instance fixes.
- Items 3, 5 and 6's cross-references honoured rather than duplicated.
- Item 4 connected to T-3985's subject-count work.