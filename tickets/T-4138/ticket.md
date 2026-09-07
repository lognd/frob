---
id: T-4138
title: TEST002 renders an absent coverage artifact as a measured zero, reporting 135
  false per-symbol errors against a TypeScript stack whose bound tests pass
state: queued
kind: bug
origin: agent
created: '2026-09-07'
priority: critical
parent: null
tier: ticket
sprint: alpha-gate
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/__init__.py
- src/frob/gates/_coverage*.py
- tests/**/test_test002*
- tests/**/*coverage*
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/__init__.py
  reason: TEST002 conflates absent coverage artifact with measured zero; fix distinguishes
    three states and audits shared loader consumers
  actor: logan
  at: '2026-09-07'
- op: add
  glob: src/frob/gates/_coverage*.py
  reason: TEST002 conflates absent coverage artifact with measured zero; fix distinguishes
    three states and audits shared loader consumers
  actor: logan
  at: '2026-09-07'
- op: add
  glob: tests/**/test_test002*
  reason: TEST002 conflates absent coverage artifact with measured zero; fix distinguishes
    three states and audits shared loader consumers
  actor: logan
  at: '2026-09-07'
- op: add
  glob: tests/**/*coverage*
  reason: TEST002 conflates absent coverage artifact with measured zero; fix distinguishes
    three states and audits shared loader consumers
  actor: logan
  at: '2026-09-07'
designated_repro_test: null
acceptance:
- text: given a symbol with bound passing test cases and no coverage artifact, when
    gate TEST runs, then it reports the symbol as unmeasured rather than emitting
    TEST002
  evidence: []
- text: given a coverage artifact that genuinely records fewer than the minimum cases
    for a symbol, when gate TEST runs, then TEST002 is emitted exactly as today
  evidence: []
- text: given an absent artifact versus an artifact recording zero for a covered file,
    when each is evaluated, then the two produce different output
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
A MISSING COVERAGE ARTIFACT RENDERS AS 135 PER-SYMBOL "0 collected unit case(s)"
ERRORS. Reported as logand.app-v2 F-340. Their agent traced TEST002 on a brand
new component to a coverage loader reporting no coverage artifact, and confirmed
the SAME rule fires on files that have been tested for a long time. The bound
test cases exist and pass; the runner is vitest; there is simply no coverage
artifact of the shape frob reads.

THIS IS THE DOMINANT DEFECT CLASS, AT ITS LARGEST OBSERVED SCALE. An ABSENT
measurement is being rendered as a MEASURED ZERO, and then the zero is enforced
against 135 symbols. Every one of those errors asserts something false: it says
these symbols have no collected unit cases, when the truth is that nothing
counted them. The remedy the rule implies -- go write tests -- is already done,
so following it cannot clear the finding. That makes it a no-exit as well.

THE CODE ALREADY KNOWS THE RIGHT POSTURE, FOUR HUNDRED LINES AWAY, and that is
the strongest argument for the fix. `_test001_zero_measured_branch_coverage`
(src/frob/gates/__init__.py, around line 3982) documents it explicitly: it
returns no override "when the symbol was never measured at all ... a measurement
gap is TEST006's territory, not proof this symbol's binding is vacuous."

That is exactly the distinction TEST002's count path fails to make. In
`_test001_test002_verdict` (around line 3957):

    effective = _case_count(valid, tests, Path(snapshot.root)) if edges
                else _inferred_unit_cases(record.symref, tests)
    ...
    if effective < cfg.min_unit_cases:
        return _test002_below_min(record, effective, cfg)

`effective == 0` because the artifact is missing is indistinguishable here from
`effective == 0` because no cases exist. One neighbouring rule guards the
distinction and this one does not. Two rules in one module with opposite
postures on the same question is the desync frob exists to prevent.

THE SECOND HALF IS THE PYTHON-DEFAULT CLASS, and it is why the consumer hit this
and we never will. The artifact frob reads is the one a python coverage run
produces. Their stack is TypeScript with vitest, which does not produce it by
default. So the loader finds nothing, every TS symbol counts zero, and the whole
TS surface reports as untested while its tests pass. This repo has recorded seven
prior instances of code paths assuming python; this is the eighth, and the most
expensive so far. Our own green here is evidence of nothing -- we produce the
artifact, so the branch never executes.

WHAT TO DO -- and the first item is the fix; the rest is what makes it stay fixed
  1. WHEN THE COVERAGE ARTIFACT IS ABSENT, TEST002 MUST REPORT UNMEASURED, NOT
     ZERO. Follow the neighbouring rule's precedent exactly: a measurement gap is
     a different verdict from a measured zero, and it must not be enforced as an
     error against every symbol. Say "unmeasured" in the output; do not silently
     pass either, which would be the same bug facing the other way.
  2. Distinguish the three states that are currently two: no artifact at all; an
     artifact that does not cover this file; an artifact covering the file that
     records zero cases. Only the third is a real TEST002.
  3. Let the runner produce what frob reads, OR read what the runner produces.
     The consumer names both options and does not choose. Prefer counting
     collected cases from the runner's own JSON reporter over demanding a
     python-shaped artifact from a non-python stack -- a rule that requires a
     foreign toolchain to emit a foreign format will be worked around, not
     adopted.
  4. Audit every other gate that loads this artifact for the same conflation.
     The loader is shared; the posture is per-rule. Report the count either way.

MUST-FIRE FIXTURE:   a symbol with bound, passing, non-python test cases and NO
                     coverage artifact reports unmeasured, not a TEST002 error.
MUST-STAY-QUIET:     a symbol with a coverage artifact that genuinely records
                     fewer than the minimum cases still reports TEST002 exactly
                     as today.
THIRD FIXTURE:       an absent artifact and an artifact recording zero for a
                     covered file produce DIFFERENT output -- the two states must
                     never print the same sentence.

ACCEPTANCE
- TEST002 reports unmeasured rather than zero when the artifact is absent, and
  does not silently pass instead.
- The three states are distinguished in both logic and output.
- A non-python runner's collected cases can be counted without producing a
  python-shaped artifact, or that decision is explicitly deferred with a reason.
- Every other consumer of the shared coverage loader audited for the same
  conflation, with the count reported.
- All three fixtures committed.
