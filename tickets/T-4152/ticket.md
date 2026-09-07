---
id: T-4152
title: the done-report generator never emits the captured-claims section its own land
  verifier reads, so post-merge re-verification is skipped by default
state: queued
kind: bug
origin: agent
created: '2026-09-07'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_done_report.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: 'retracts this ticket''s central premise: an emitter DOES exist, referencing
    the heading through a constant, and my literal-string search could not see it.
    Records the method error, folds in consumer report F-358 which states the opposite
    complaint, and restates the part that survives -- the land silently downgrading
    when the section is absent'
  actor: logan
  at: '2026-09-07'
  old_length: 4774
  new_length: 7984
designated_repro_test: null
acceptance:
- text: given a done report produced by the done-report verb, when it is written,
    then it carries a captured-claims section whose numbers come from the gate run
    that produced it
  evidence: []
- text: given an existing report that already carries the section, when it is parsed,
    then it behaves exactly as today and is not rewritten
  evidence: []
- text: given a land whose ticket report carries a generated section, when the land
    runs, then post-merge re-verification is performed rather than reported skipped
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
FROB'S DONE-REPORT GENERATOR NEVER WRITES THE SECTION FROB'S OWN LAND VERIFIER
REQUIRES, so post-merge re-verification is skipped whenever an author happens not
to hand-write it. Reported as logand.app-v2 F-353, whose closing sentence is the
whole finding: "verified=SKIPPED-UNMEASURED is the steady state of every
LAND-PROOF in this repo."

MEASURED HERE, 2026-09-07:

    done-reports in this repository            3066
    carrying a `### Captured claims` section   2373  (77%)
    NOT carrying one                            693  (23%)

    occurrences of that heading in src/        emitters: NONE
                                               readers:  4 (the land's
                                               re-verification, the rapid
                                               sweep, the verify path, and
                                               the claims parser)

So four call sites READ a section nothing WRITES. Every one of those 2373 was
produced by an author following prose guidance, and the 693 are the ones where
that did not happen. The consumer's phrasing is exactly right and is the reason
this is a tool defect rather than an authoring habit: THE AGENT CANNOT KNOW THE
FORMAT. Frob asks for a structure it does not generate, then silently downgrades
its own strongest post-land check when the structure is absent.

WE ARE NOT IMMUNE, WHICH IS THE PART I WANT ON THE RECORD. Earlier today a land
in this repository reported `LAND-PROOF verified=SKIPPED-UNMEASURED` and it was
read -- correctly, per current behaviour -- as "rapid profile posture, not a land
failure". That is the same downgrade, on our own main, treated as normal. Our 77%
means we notice it less often than the consumer does, not that we are protected.

WHY THIS RANKS HIGH DESPITE PRESENTING AS A WARNING. The land proof is the check
that answers "did this ticket's code actually reach main, and do its claims still
hold after the merge". This repo has a recorded incident where a land marked a
ticket done with ZERO code landed, and another where a land proof verified
ancestry rather than content. The re-verification is the guard against exactly
that class, and it is being skipped by default for a formatting reason. A guard
that is off unless the author remembered a heading is not a guard.

IT IS ALSO A SILENT ZERO IN THE PRECISE SENSE THIS QUEUE KEEPS FINDING: "gate
status UNKNOWN" is emitted as a warning and then treated as an acceptable pass.
Unmeasured and verified must not share an outcome.

THE FIX THE CONSUMER PROPOSES IS THE RIGHT ONE, AND THE FIRST HALF IS THE REAL
FIX: the done-report verb should emit the captured-claims section ITSELF, from
the gate run it has just performed. It has the numbers; the author does not, and
asking the author to transcribe them is how they drift.

WHAT TO DO
  1. Make the done-report generator emit the section, populated from the gate run
     it performed rather than from anything the author typed. This is the fix.
  2. Their second suggestion -- accept the flat form's existing gate line as the
     claim -- is a reasonable COMPATIBILITY measure for the 693 existing reports
     and for hand-written ones, but it must not replace (1). Parsing whatever
     prose an author wrote is how we got here.
  3. Decide what a land should do when the section is genuinely absent and cannot
     be reconstructed. Today it warns and proceeds. Given the incidents above,
     consider whether an unverifiable land should be refused rather than
     downgraded -- and if it should still proceed, say so explicitly with a
     reason, so the next reader knows it was chosen rather than inherited.
  4. Re-measure the 693 after the fix. They are historical artifacts and must NOT
     be rewritten -- this repo has already established that landed done reports
     are historical records -- but the count tells you whether new reports are
     still being produced without the section.

MUST-FIRE FIXTURE:   a done report produced by the verb carries a captured-claims
                     section whose numbers match the gate run that produced it.
MUST-STAY-QUIET:     an existing hand-written report that already carries the
                     section is parsed exactly as today, and no historical report
                     is rewritten.
THIRD FIXTURE:       a land whose ticket's report carries a generated section
                     performs the post-merge re-verification rather than
                     reporting it skipped.

ACCEPTANCE
- The generator emits the section from its own measurement.
- The absent-section policy decided explicitly, not inherited.
- Historical reports left unmodified.
- The proportion of new reports lacking the section measured after the fix.
- All three fixtures committed.

RETRACTION -- THIS TICKET'S CENTRAL PREMISE IS FALSE. I wrote above that the
generator "never emits" the captured-claims section and that four call sites read
a section nothing writes. THAT IS WRONG. There IS an emitter:

    src/frob/tickets/_models.py:1022   _CLAIMS_HEADING = "### Captured claims"
    src/frob/tickets/_models.py:1165   lines = [_CLAIMS_HEADING, ...]
    src/frob/tickets/_reporting.py:559 calls _capture_done_report_claims(...)

HOW I GOT IT WRONG, and the method error matters more than the fact: I searched
for the LITERAL STRING "Captured claims" across the source and found only
docstrings and parsers, then concluded no writer existed. The writer references
the heading through a CONSTANT, so a literal search cannot see it. This project's
standing directive is that checks must compare parsed symbols rather than
substrings; I applied a substring search to a question about symbols and reached a
confident wrong answer. The same error in a gate is a class this queue has filed
eleven times.

A CONSUMER REPORT ARRIVING AFTER THIS TICKET STATES THE OPPOSITE COMPLAINT, and
between the two the real shape is visible. F-358: the done-report verb ALWAYS
appends its own Changed / Evidence / Captured-claims sections, so the flat
heading-only form their repo uses cannot be produced through the verb at all. So
the verb emits; it is reports NOT produced by the verb that lack the section.

WHAT SURVIVES, restated honestly. The measured facts are unchanged: 2373 of 3066
done reports here carry the section and 693 do not, and a land whose report lacks
it downgrades to an unverified outcome that reads like a pass. The defect is NOT
a missing emitter. It is that:

  1. A report can reach a land WITHOUT having gone through the verb -- hand
     written, or written by an agent following prose -- and nothing requires that
     it did. The section is therefore optional in practice while the verifier
     treats its absence as an acceptable skip.
  2. THE LAND'S RESPONSE TO A MISSING SECTION IS THE REAL BUG. It warns and
     proceeds, so unmeasured and verified share an outcome. That half of the
     original ticket stands entirely and is the part to fix: either regenerate
     the section from the verb at land time, or refuse the land, but do not
     silently downgrade the strongest post-land check for a formatting reason.
  3. F-358 adds a genuine second defect in the other direction: the verb offers
     no way to produce the flat form, so a repo that wants it must hand-write --
     which is precisely how a report ends up without the section. The two
     findings are the same loop. Fixing only one leaves the other producing
     victims.

REVISED DIRECTION FOR WHOEVER WORKS THIS
- Do not "add an emitter". Read the existing one first.
- Decide what a land does when the section is absent, and make unmeasured
  distinguishable from verified in the output. That was and remains the point.
- Handle F-358's half: either the verb can produce the flat form, or the flat
  form is documented as unsupported. Silently supporting it in practice while the
  verifier requires the other shape is the state that produced both reports.
- Historical reports stay unmodified.
