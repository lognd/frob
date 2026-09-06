---
id: T-3985
title: 'subject-count primitive: enforcing gate with zero subjects is a finding'
state: in-progress
kind: invariant
origin: agent
created: '2026-09-06'
priority: critical
parent: T-3984
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/process/parsers/common.py
- src/frob/check/_python.py
- src/frob/gates/_profile_boundary.py
- tests/unit/test_process.py
- tests/unit/test_check.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/check/_python.py
  reason: T-3985's design requires wiring subject_count from common.py's model into
    the check pipeline's family-result construction and PROFILE001 (the proven T-3941
    positive control) as the proof-of-concept, per the ticket body's own acceptance
    criterion 3
  actor: logan
  at: '2026-09-06'
- op: add
  glob: src/frob/gates/_profile_boundary.py
  reason: T-3985's design requires wiring subject_count from common.py's model into
    the check pipeline's family-result construction and PROFILE001 (the proven T-3941
    positive control) as the proof-of-concept, per the ticket body's own acceptance
    criterion 3
  actor: logan
  at: '2026-09-06'
- op: add
  glob: tests/unit/test_process.py
  reason: T-3985's design requires wiring subject_count from common.py's model into
    the check pipeline's family-result construction and PROFILE001 (the proven T-3941
    positive control) as the proof-of-concept, per the ticket body's own acceptance
    criterion 3
  actor: logan
  at: '2026-09-06'
- op: add
  glob: tests/unit/test_check.py
  reason: T-3985's design requires wiring subject_count from common.py's model into
    the check pipeline's family-result construction and PROFILE001 (the proven T-3941
    positive control) as the proof-of-concept, per the ticket body's own acceptance
    criterion 3
  actor: logan
  at: '2026-09-06'
- op: add
  glob: src/frob/check/_python.py
  reason: T-3985's design requires wiring subject_count from common.py's model into
    the check pipeline's family-result construction and PROFILE001 (the proven T-3941
    positive control) as the proof-of-concept, per the ticket body's own acceptance
    criterion 3
  actor: logan
  at: '2026-09-06'
- op: add
  glob: src/frob/gates/_profile_boundary.py
  reason: T-3985's design requires wiring subject_count from common.py's model into
    the check pipeline's family-result construction and PROFILE001 (the proven T-3941
    positive control) as the proof-of-concept, per the ticket body's own acceptance
    criterion 3
  actor: logan
  at: '2026-09-06'
- op: add
  glob: tests/unit/test_process.py
  reason: T-3985's design requires wiring subject_count from common.py's model into
    the check pipeline's family-result construction and PROFILE001 (the proven T-3941
    positive control) as the proof-of-concept, per the ticket body's own acceptance
    criterion 3
  actor: logan
  at: '2026-09-06'
- op: add
  glob: tests/unit/test_check.py
  reason: T-3985's design requires wiring subject_count from common.py's model into
    the check pipeline's family-result construction and PROFILE001 (the proven T-3941
    positive control) as the proof-of-concept, per the ticket body's own acceptance
    criterion 3
  actor: logan
  at: '2026-09-06'
body_changes:
- mode: append
  reason: T-4025 item 1 is another instance of the subject-count primitive (reachability-from-entrypoint
    is a zero-subjects-examined shape); cross-referencing per the coordinator's instruction
    rather than filing a duplicate
  actor: logan
  at: '2026-09-06'
  old_length: 3748
  new_length: 4648
- mode: append
  reason: T-4036 item 4 (include!'d file invisible to gate:TEST/DOC/REF) is another
    subject-count instance, applied to the walker; cross-referencing rather than duplicating
  actor: logan
  at: '2026-09-06'
  old_length: 4648
  new_length: 5741
- mode: append
  reason: F-273 M-1 is a second independent instance of T-4025 item 1's reachability
    gap, now with the most concrete rule proposal yet; cross-referencing rather than
    filing a third time
  actor: logan
  at: '2026-09-06'
  old_length: 5741
  new_length: 7071
designated_repro_test: null
acceptance:
- text: given the design step, when it completes, then it states an explicit checkable
    definition of enforcing (which gates/severities qualify) and how a legitimate
    zero-subject case (e.g. a language-specific rule in a repo without that language)
    is distinguished from a defect
  evidence: []
- text: given T-3844's promotion list, when this ticket's design step completes, then
    it reports whether a subject count would have flagged any of the 308 promoted-to-error
    rules as never-exercised rather than clean
  evidence: []
- text: given ToolResult gains a subject_count field, when PROFILE001 (T-3941's proven
    positive control) is wired to populate it, then a repro of the T-3941 Windows
    path-mismatch bug shows subject_count == 0 on an enforcing gate and the new cross-cutting
    check fires
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-3984's cross-cutting ask, and the FIRST child per the epic's own explicit instruction -- file and design this before any of the thirteen numbered items, several of which (1, 2, 4, 5, 12) are instances of this one primitive.

THE CONSUMER'S OWN FRAMING: "frob measures findings; it does not measure whether a check had any SUBJECTS. The single highest-value change would be for every gate and every repo-side process test to report its subject count, and for a zero subject count on a gate configured to be enforcing to be a finding in its own right."

WE PROVED THIS INDEPENDENTLY TODAY, THREE TIMES, IN OUR OWN CODE:
- T-3941: PROFILE001 returned the empty tuple unconditionally on Windows because xref emitted backslash paths that never matched a forward-slash prefix. It reported a clean tree while examining nothing; only a FAILING POSITIVE CONTROL caught it.
- T-3947 and T-3948: two more gates with the identical shape.
A subject count would have shown 0-of-N on the very first Windows run of PROFILE001, no positive control needed.

WHY THIS IS ONE MECHANISM, NOT THIRTEEN: item 1 (POL000, a policy.pattern matching zero nodes), item 2 (VMOD002/003, a test node's runnable unresolved), item 4 (TESTRUN001, a configured runner producing no tool result), item 5 (skipped evidence not counting), and item 12 (TESTMOCK001, fully-mocked subjects) are each "this check ran over zero (or zero real) subjects and that fact was invisible." Building the primitive first makes each of those a thin consumer of one shared field/check rather than a bespoke implementation.

TWO DESIGN CONSTRAINTS THAT MUST BE ANSWERED IN THIS TICKET'S DESIGN STEP, NOT LEFT IMPLICIT:

1. A ZERO SUBJECT COUNT IS NOT ALWAYS A DEFECT. A rule for a language this repo does not use has zero subjects legitimately (e.g. a Kotlin-only rule in a repo with no Kotlin). The new finding must be "an ENFORCING gate reported zero subjects," and "enforcing" must be an EXPLICIT, checkable definition (e.g. severity=error and not carved out by a declared applicability condition) -- not "every gate with subjects=0." Get this wrong and it becomes noise that gets waived, which is the worst outcome per the consumer's own words and this repo's own WAIVE004 lesson (an escape matching the normal case disables the guard).

2. THIS INTERSECTS T-3844'S TWO-KINDS-OF-ZERO PROBLEM (read T-3844 before designing): zero findings because the code is clean, versus zero findings because the condition/subject never arose. T-3844 measured findings-by-rule at the SEVERITY layer and could not distinguish these -- a rule promoted to error while genuinely clean is fine; a rule promoted to error while silently examining nothing is exactly the PROFILE001 shape. The subject count is precisely the missing signal T-3844's own measurement could not see. Design how a subject count would have changed T-3844's promotion decisions (would any of the 308 promoted-to-error zero-finding rules have shown a zero SUBJECT count, meaning they were never really exercised rather than clean) as part of validating this design.

SCOPE: add a subject_count (or subjects_examined) field to the shared ToolResult/diagnostic-emitting model (src/frob/process/parsers/common.py::ToolResult) that every gate/check populates, plus a new cross-cutting check (run after normal gate execution, reading the collected results) that flags any ENFORCING gate reporting subject_count == 0. This is infrastructure work touching many gates' call sites to populate the field -- scope the FIRST landing to the model change plus the cross-cutting check plus 2-3 gates as a proof of concept (PROFILE001/T-3941's own gate is the obvious first target, since it is the proven positive control), not a repo-wide rollout in one ticket.


T-4025 item 1 is another instance of this ticket's own primitive, cross-referenced rather than duplicated. FINDING: a frontend component fully implemented, tested, and V-model-closed, that is NEVER INVOKED from any real entrypoint -- frob knows package.json declares an entrypoint and knows the script names, but does not model REACHABILITY from a declared entrypoint down to the component. This is a vacuous-pass shape at the component-invocation level rather than the gate level: three green, closed components that nothing calls is exactly "a check with a subject count of zero" one layer further down the call graph. Fold this into the design step's scope: does the subject-count primitive generalize to "is this V-model-closed unit ever reached from a declared entrypoint," or does that need its own reachability pass reusing the same callgraph BFS machinery already proven for COV006/T-3962.


T-4036 item 4, cross-referenced rather than duplicated -- a further instance of this ticket's own subject-count primitive. FINDING: a source file included via a language's include!/#include-style mechanism rather than declared as a proper module (e.g. Rust's mod declaration) is invisible to gate:TEST, gate:DOC, and gate:REF simultaneously -- all three walk the module tree, none of them walk raw includes, so all three report CLEAN on a file with real code, two real callers, and doc comments that none of them ever reads. This is three gates independently examining a subject set that silently excludes a real, live file -- exactly the "0 findings over 0 subjects examined, indistinguishable from 0 over N" shape this ticket exists to fix, just triggered by a walker gap rather than a path-separator or reachability bug. Their own fallback ask is precisely the primitive applied to the walker: report an unwalked-but-tracked source file (present in git, matched by no language walker's subject set) as a finding in its own right, distinct from a clean pass over files the walker DID see.


F-273 M-1, cross-referenced rather than refiled -- a SECOND independent instance of T-4025 item 1 (itself appended to this ticket above), now with the MOST CONCRETE proposal yet. VERIFIED: WIRE001 is the closest existing rule and it is explicitly disabled for this shape (see the many frob:waive WIRE001 directives already on this consumer's backend routes) -- so the gap is not that no rule exists, but that the closest rule was deliberately turned off for exactly the case that needed it.

FINDING: COMP-1801..1805 (auth pages) each carry a frob:describes anchor, a frob:doc back-reference, and a passing unit test -- V-model closure satisfied purely by "component exists and is tested" -- while the pages are UNROUTED and unreachable in production. Proposed concrete rule: a frontend WIRE rule asserting every exported page component under pages/** is referenced from a route table, SYMMETRICAL to the backend's existing route-registration check (whatever machinery already verifies a backend route handler is registered, mirror it for frontend page components against their router config). This is the first of the reachability-primitive instances with a fully specified, implementable proposal rather than only a description of the gap -- prioritize it as the design's worked example when this ticket's scope is picked up.
