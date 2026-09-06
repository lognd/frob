---
id: T-3985
title: 'subject-count primitive: enforcing gate with zero subjects is a finding'
state: queued
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
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
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
