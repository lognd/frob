---
id: T-2480
title: check-repro's fixed 60s budget turns a slow but valid repro test into an indistinguishable
  NO_VERDICT
state: queued
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_evidence.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: Given a repro test that exceeds the check-repro time budget, when it is checked,
    then the result reports a timeout distinctly from a test that ran and did not
    reproduce.
  evidence: []
- text: Given a fast test that genuinely does not fail at the parent commit, when
    it is checked, then it is still rejected, proving BUG002's real check was not
    weakened.
  evidence: []
- text: Given a fast genuinely-reproducing test, when it is checked, then it verifies
    through the normal path with no added friction.
  evidence: []
threat: null
component: tickets
anchor: false
anchor_reason: null
land_commit: null
---
`frob ticket evidence --check-repro` / `--designate-repro` runs the
candidate repro test in a subprocess under a FIXED 60s budget
(`_BUG_REPRO_TIMEOUT_S`). A test that legitimately takes longer returns
`NO_VERDICT`, which reads as "reproduction could not be demonstrated"
-- indistinguishable, to a reader, from a genuinely confirmatory-only
test that the gate is right to reject.

MEASURED instance (T-2463): the designated repro loads and elaborates
the FULL strata design plus the entire SYS gate, which exceeds 60s on
this machine. The agent verified the fail-at-parent / pass-at-fix shape
BY HAND instead -- committed the test alone, confirmed it FAILED with 5
unexpected SYS violations against the unfixed strata file, restored the
fix, confirmed it passed -- and then used `--designate-repro-force`
with that transcript as the recorded reason.

That was the correct handling and the disclosure was complete. But note
what the workflow required: a correct, genuinely-reproducing test forced
the agent onto the FORCE path, which is the same escape hatch used when
a repro truly cannot be demonstrated. The audit trail now cannot
distinguish "forced because the tool timed out on a slow but valid
test" from "forced because no reproduction exists", except by reading
the free-text reason. Every additional legitimate use of `--force`
erodes the signal that `--force` was meant to carry.

WHY THE TIMEOUT IS THE WRONG SHAPE HERE. Repro tests for
architecture/design-level defects are inherently slow, because
demonstrating the defect means elaborating the whole model. So the
tests most likely to exceed the budget are precisely the ones covering
the broadest, highest-consequence defects. A fixed 60s ceiling
selectively disenfranchises the most valuable repro tests.

Also relevant: this repo has just spent significant effort establishing
that a budget which DROPS work while reporting a clean-looking result
is a false-green generator (T-2456: the land check's 300s budget was
silently dropping an entire stage group from every sweep). This is the
same shape at a smaller scale -- a fixed budget converting "did not
finish" into a verdict.

FIX SHAPE:
  - `NO_VERDICT` due to TIMEOUT must be reported distinctly from
    `NO_VERDICT` due to the test not reproducing. They are different
    facts and only one of them is evidence about the ticket. This is
    the fail-loudly doctrine (T-2391) applied to the repro checker:
    "could not measure" is not "measured and found nothing".
  - Make the budget configurable, and/or scale it -- a per-invocation
    override, or a longer default for tests the caller marks as
    design-level. Do not simply raise the constant and leave the same
    cliff further out.
  - Consider whether a timeout should auto-permit the force path with
    the timeout recorded as the structured reason, so the audit trail
    distinguishes the two cases mechanically rather than by prose.

POSITIVE CONTROLS:
  - must-distinguish: a test that exceeds the budget reports a TIMEOUT
    outcome, not a bare NO_VERDICT.
  - must-still-refuse: a fast test that genuinely does NOT fail at the
    parent commit is still rejected. Do not fix the timeout by
    weakening BUG002's actual check, which has caught real
    confirmatory-only evidence repeatedly.
  - must-still-complete: a fast, genuinely-reproducing test still
    verifies within the normal path with no added friction.
