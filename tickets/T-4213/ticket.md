---
id: T-4213
title: four discarded Results found by the first typani lint run this tree has ever
  had, one of them confirming an open critical ticket's exact call site
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
- src/frob/gates/_coverage.py
- src/frob/serve/_daemon.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given a newly added discarded Result, when the lint runs, then it is reported
  evidence: []
- text: given a Result deliberately discarded with an explicit reason at the call
    site, when the lint runs, then it is not reported
  evidence: []
- text: given the non-unwind sites named in this ticket, when the lint runs after
    the fix, then none of them reports
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
FOUR DISCARDED RESULTS, FOUND THE FIRST TIME THE TYPANI LINT WAS EVER RUN AGAINST
THIS TREE. One of them is independent confirmation of an already-open critical
ticket.

The lint could not run here at all until now -- our dependency floor permits a
typani old enough to have no lint module, which is filed separately. Running it
through a temporary newer typani, without touching the lock:

    653 files scanned, 701 findings
      4 ERROR   (TYP003, a Result or Option whose value is never inspected)
    697 info    (mostly propagation-style suggestions)

THE FOUR ERRORS, and they are the whole of this ticket -- the info findings are
style and are explicitly NOT in scope:

    src/frob/gates/_coverage.py:1083     write_coverage_lock
    src/frob/serve/_daemon.py:554        _poll_verify_worker
    src/frob/tickets/_land.py:2216       _land_plan_unwind_after_merge
    src/frob/tickets/_land.py:6959       _check_tdd_order

A DISCARDED RESULT IS THE SILENT-FAILURE SHAPE THIS QUEUE EXISTS TO FIND. The
whole point of returning a Result is that the caller must decide what a failure
means. Dropping it converts every error path into a success path with no
diagnostic, which is the same class as an unmeasured gate reading as clean -- and
this project's own engineering rules require fallible operations to return a
Result precisely so this cannot happen silently.

THE THIRD ONE CONFIRMS AN OPEN CRITICAL TICKET FROM A DIFFERENT DIRECTION. T-3848
is titled "land unwind failure is discarded: a failed merge whose unwind also
fails leaves ...". The lint independently flags exactly that call site:

    merged_finalized, own_commits = _land_plan_merge_and_finalize(root, worktree)
    if merged_finalized.is_err:
        _land_plan_unwind_after_merge(root, pre_merge_sha, own_commits, ...)
        return Err(merged_finalized.danger_err)

The unwind runs on the failure path and its own Result is dropped, so a merge that
fails AND whose unwind also fails returns the merge's error and says nothing about
the unwind. T-3848 was filed from reasoning; this is a mechanical confirmation of
the same site. Attach this evidence there and fix that one under T-3848 rather
than here.

THE OTHER THREE NEED TRIAGE, NOT A BLANKET FIX. Each discarded Result is a
decision someone made or forgot, and the honest fix differs:
  - if the failure genuinely does not matter, say so at the call site with an
    explicit discard and a reason, so the next reader and the next lint run both
    know it was deliberate;
  - if it matters, propagate or handle it.
Do NOT wrap all four in a blanket suppression to clear the lint. Two of these are
on the land path, which this repository has already had to debug for silent
failures more than once.

WORTH RECORDING SEPARATELY: this lint has apparently never run against this
codebase, and its first run found four real silent-failure sites plus a
corroboration of an open critical ticket. That is the concrete cost of the stale
dependency floor filed as its own ticket -- the check was written down as a house
rule, and no environment could execute it.

MUST-FIRE FIXTURE:   a newly added discarded Result is reported.
MUST-STAY-QUIET:     a Result that is deliberately discarded with an explicit
                     reason is not reported.
THIRD FIXTURE:       the three sites fixed here no longer report, and the land
                     unwind site is left to its own ticket.

ACCEPTANCE
- Each of the three non-unwind sites triaged individually, with the decision
  recorded at the call site.
- The unwind site's evidence attached to T-3848, not fixed here.
- No blanket suppression used.
- All three fixtures committed.
