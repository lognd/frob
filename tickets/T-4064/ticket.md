---
id: T-4064
title: 'F-270: REF002 misses relative TS imports, so an imported module reads as unreferenced
  and needs a waiver'
state: queued
kind: bug
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
- src/frob/gates/_refs.py
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
Consumer logand.app-v2 F-270, 2026-09-06:

  "frontend/src/engine/canvasRuns.ts IS IMPORTED by AsciiCanvas.tsx with a
   RELATIVE PATH (./canvasRuns) and still got REF002 ('no second consumer'),
   forcing a `frob:waive REF002`. The inbound-reference scanner should resolve
   relative TS imports the same way it resolves ALIAS imports."

REF002 REPORTED A FILE AS UNREFERENCED THAT IS DEMONSTRABLY IMPORTED. The import
exists, in the same repo, in a file frob parses. The reference resolver simply
does not follow `./`-relative TypeScript specifiers, so an entire class of real
edges is invisible and the file reads as an orphan.

THIS IS A FALSE POSITIVE ON A RULE WHOSE WHOLE PURPOSE IS COUNTING CONSUMERS, and
that makes it worse than an ordinary miss. REF002's judgement IS the inbound
count; if the count is wrong the verdict is meaningless, and the only remedy
available to the user is a waiver -- so the repo accumulates `frob:waive REF002`
comments that document a tool limitation rather than a code decision. This
session has already collected the argument against that: a waiver written for a
tooling reason is a durable artifact that outlives its cause and degrades every
real waiver's signal (T-4054, T-4063).

NOTE THE ASYMMETRY THE CONSUMER IDENTIFIES: ALIAS imports ARE resolved, relative
ones are not. So the resolver is not missing TypeScript support wholesale -- it
handles one specifier form and drops the other. That is a narrower and more
tractable bug than "no TS support", and it suggests the fix is completing an
existing resolver rather than building one.

THIS IS THE SECOND STRUCTURAL GAP IN THE SAME LANGUAGE'S GRAPH, and the two
should be read together: T-4016 records that the TS walker emits NO SYMBOL for
`describe()`/`it()` call expressions, so no `frob:tests` directive can bind a
vitest test. Now the same subsystem also fails to resolve relative imports. Both
are cases where TypeScript is parsed but its graph is incomplete in a way that
makes a gate produce a confident wrong answer. WHOEVER TAKES EITHER SHOULD ASK
WHETHER THE TS GRAPH HAS A DEFINED COMPLETENESS CONTRACT AT ALL -- two independent
holes suggest nobody has enumerated what it is meant to represent.

VERIFY BEFORE BUILDING: find where TS imports are turned into reference edges and
confirm the alias/relative asymmetry rather than assuming the consumer's
description. Their symptom is reliable; the mechanism is a hypothesis until
grepped -- I have been wrong twice this session by accepting a plausible
mechanism.

CONSIDER THE SUBJECT-COUNT ANGLE (T-3985): a resolver that finds zero inbound
references for a file could distinguish "scanned and found none" from "found no
specifiers it knows how to resolve". The second is what happened here, and it is
reportable rather than silent.

MUST-FIRE FIXTURE: a genuinely unreferenced TS module still gets REF002.
MUST-STAY-QUIET: a module imported ONLY via a relative specifier does not get
REF002, and needs no waiver.
THIRD FIXTURE: alias and relative specifiers resolve to the same edge for the
same target -- asserted together, so the asymmetry cannot silently return.

ACCEPTANCE
- The alias/relative asymmetry confirmed in source before any change.
- Relative TS specifiers resolved into inbound reference edges.
- Whether the TS graph has a stated completeness contract, answered; if not, say
  so and cross-reference T-4016.
- All three fixtures committed.