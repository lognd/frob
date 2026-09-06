---
id: T-4067
title: 'F-272: the TS walker rejects syntax vitest runs fine, and the parse failure
  cascades into false TEST002/REF002 findings'
state: queued
kind: bug
origin: human
created: '2026-09-06'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/lang/_walk_typescript.py
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
Consumer logand.app-v2 F-272, 2026-09-06:

  "gate:PARSE reports PARSE002 on frontend/tests/unit/pages/projects.test.tsx
   (AND TEST002/REF002 FOLLOW FROM IT) while vitest parses and runs ALL 22 CASES
   in that file. The frob TS walker rejects some syntax (likely vi.doMock +
   dynamic import or a `satisfies` clause) that esbuild accepts; THE WALKER SHOULD
   REPORT THE OFFENDING LINE AND CONSTRUCT."

A PARSE FAILURE CASCADES INTO FALSE FINDINGS FROM UNRELATED GATES. That is the
part to fix first. When the walker cannot parse a file, TEST002 and REF002 then
report on a file whose symbols and edges were never extracted -- so a parse
problem is laundered into confident-sounding coverage and reference verdicts
about code that frob simply did not read. The user sees three findings and only
one of them is real.

THIS IS A SUBJECT-COUNT INSTANCE, and a particularly clean one: the downstream
gates have ZERO subjects for this file because parsing failed, and they report as
though they had examined it. T-3985's primitive is exactly the mechanism that
would make this impossible to state silently. Cross-reference it; a parse failure
should POISON the downstream verdicts for that file rather than yielding empty
ones.

THE DIAGNOSTIC ASK IS THE CHEAP HALF AND SHOULD SHIP REGARDLESS: "the walker
should report the offending line and construct". Today PARSE002 says a file
failed to parse without saying WHERE or WHY, so the consumer had to GUESS the
cause -- their own report offers two candidates (`vi.doMock` plus a dynamic
import, or a `satisfies` clause) because the message gave them nothing. tree-
sitter reports error nodes with positions; surfacing the first one costs almost
nothing and turns an unactionable finding into a fixable one.

THIS IS THE THIRD STRUCTURAL HOLE IN THE TS GRAPH IN ONE DAY, and together they
make the case that the subsystem needs a stated contract rather than three
patches:
  T-4016  the walker emits NO SYMBOL for describe()/it() call expressions, so no
          frob:tests directive can bind a vitest test
  T-4064  REF002 does not resolve RELATIVE TS imports, so an imported module
          reads as unreferenced
  this    the walker REJECTS syntax that the project's own bundler accepts,
          and the failure cascades
Each was reported separately by the same consumer within hours. WHOEVER TAKES ANY
OF THE THREE should first answer: WHAT TYPESCRIPT SYNTAX DOES frob CLAIM TO
SUPPORT, and what does it do when it meets syntax outside that set? Three
independent holes suggest the answer has never been written down.

VERIFY THE SPECIFIC CAUSE RATHER THAN TAKING THE GUESS. The consumer says
"likely" -- that is a hypothesis, and this session has produced two cases where a
plausible mechanism was wrong. Reproduce the parse failure against the real file
(or a reduced case) and identify the construct precisely before changing the
grammar or the walker.

A NOTE ON SEVERITY: because the cascade produces TEST002 and REF002 findings, a
single unsupported construct can make a correctly-tested, correctly-imported file
look like it has no tests and no consumers. That is the exact shape that trains
users to distrust the gates.

MUST-FIRE FIXTURE: a genuinely unparseable file still reports PARSE002, naming
the line and construct.
MUST-STAY-QUIET: the reported file parses, and TEST002/REF002 report on its real
symbols.
THIRD FIXTURE: when parsing DOES fail, downstream gates for that file report
"not analysed" rather than an empty-set verdict.

ACCEPTANCE
- The rejected construct identified by reproduction, not by the report's guess.
- PARSE002 names the offending line and construct.
- Downstream gates cannot render an empty-set verdict for an unparsed file.
- The TS support contract question answered, cross-referencing T-4016 and T-4064.
- All three fixtures committed.