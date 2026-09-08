---
id: T-4335
title: Post-land sweep absorbs newly-introduced errors into its baseline and reports
  CLEAN
state: in-progress
kind: bug
origin: human
created: '2026-09-08'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_rapid_sweep.py
- tests/unit/rapid_sweep_suite/test_sweep_run.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/modules/tickets-verify-sweep.md
  reason: run_deferred_post_land_sweep's baseline-write contract changed (T-4335);
    the frob:doc-linked section documenting the old 'every sweep rewrites the baseline
    regardless' behavior is now false and must be corrected in the same change, not
    left drifted
  actor: logan
  at: '2026-09-08'
- op: add
  glob: docs/modules/tickets-verify-sweep.md
  reason: run_deferred_post_land_sweep's baseline-write contract changed (T-4335);
    the frob:doc-linked section documenting the old 'every sweep rewrites the baseline
    regardless' behavior is now false and must be corrected in the same change, not
    left drifted
  actor: logan
  at: '2026-09-08'
- op: remove
  glob: docs/modules/tickets-verify-sweep.md
  reason: doc closure explosion (all symbols the doc describes anywhere, not just
    this section) is disproportionate; filing a follow-up ticket instead, waiving
    DRIFT001 on the touched function with a reason pointing to it, matching this same
    file's T-2521/AFFECT001 precedent
  actor: logan
  at: '2026-09-08'
- op: add
  glob: tests/unit/rapid_sweep_suite/test_sweep_run.py
  reason: T-4335's fix is verified by both new and updated tests in this file (forcing
    both directions per the ticket's acceptance)
  actor: logan
  at: '2026-09-08'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
THE POST-LAND SWEEP ABSORBS NEWLY-INTRODUCED ERRORS INTO ITS OWN BASELINE AND
THEN REPORTS THE TREE CLEAN WHILE THEY ARE STILL THERE.

MEASURED, FROM THE SWEEP LOGS THEMSELVES, IN ORDER. Reading the last eight
per-land sweep logs in chronological order shows a clean run of zero-error sweeps,
then this transition:

  ... recorded rolling baseline of 0 error(s)   CLEAN (0 error(s), none new vs the previous sweep)
  ... recorded rolling baseline of 3 error(s)     <- the land that INTRODUCED three errors
  ... recorded rolling baseline of 3 error(s)   CLEAN (3 error(s), none new vs the previous sweep)

The three errors were introduced by one land. That land's own sweep did not report
them as new and filed nothing; it recorded them as the new baseline. Every sweep
after it now compares against that baseline, finds nothing newer, and prints
CLEAN -- while three errors sit in the tree. The line "CLEAN (3 error(s), none new
vs the previous sweep)" contradicts itself in a single sentence.

WHY THIS IS THE MOST DANGEROUS SHAPE IN THIS CODEBASE. The sweep exists to catch
exactly this: the fast land profile switches the pre-land sweep off, and the
deferred sweep is the compensating control. Its stated contract is that new errors
become a filed bug ticket. Instead, a land that introduces errors teaches the
sweep that those errors are normal. The safety net does not merely miss the
failure -- it records the failure as the definition of healthy, and every
subsequent land inherits the laundered baseline. Nothing warned anyone; the errors
were found by a human running an unscoped check by hand.

THE DESIGN QUESTION TO SETTLE, AND IT IS THE WHOLE TICKET. A rolling baseline is
the right idea for tolerating a pre-existing backlog without blocking every land
on it. What it must not do is absorb errors that arrived WITH the land being
swept. Those two cases are distinguishable: an error identity present before the
land is inherited debt; an identity that first appears in the swept commit is
newly introduced and is precisely what the mechanism was built to catch. Make the
sweep tell them apart, and let only the first kind enter the baseline.

BE CAREFUL WITH THE FIRST-RUN CASE. When there is no prior baseline at all,
recording what is found is correct and must stay -- otherwise the first sweep
after any baseline reset would file the entire existing backlog. Distinguish
"establishing an initial baseline" from "growing an existing one", and say how.

FIX THE REPORTING LINE TOO. A summary that says CLEAN while naming a nonzero error
count should not be expressible. If the tree has errors and they are tolerated
debt, say that in those words and print the count as debt, not as clean. This
project has repeatedly paid for a measurement that reads healthy while carrying a
known fault.

VERIFY BY FORCING IT, IN BOTH DIRECTIONS. Construct a sweep over a commit that
introduces a NEW error identity and assert it is reported and filed rather than
absorbed. Then construct one over a commit that merely inherits a pre-existing
identity and assert it is tolerated and NOT re-filed. A fix confirmed only on a
clean tree proves nothing here.

Measure with `uv run frob check --json | python3 scripts/check_summary.py` rather
than grepping text -- an absent errors section is indistinguishable from a clean
one and has produced false zero reports in this repo before.
