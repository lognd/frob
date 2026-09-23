---
id: T-4810
title: Run the docstring --fix repo-wide in a coordinator-declared quiet window as
  one cross-ticket land (1055 -> N is the acceptance, agents review diffs per package)
state: queued
kind: docs
origin: human
created: '2026-09-19'
priority: medium
blocked_by:
- T-4807
parent: T-4691
tier: ticket
sprint: null
runs_last: false
milestone: 0.534.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob
- docs/modules
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.534.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
designated_repro_test: null
acceptance:
- text: given T-4807 has landed and a coordinator-declared quiet window with no in-progress
    lands, when the fix is run repo-wide as one cross-ticket land, then it applies
    in batches with frob ticket list exiting 0 after each batch
  evidence: []
- text: given the measured baseline of 1055 docstrings over 20 lines, when the sweep
    completes, then scratchpad/struct.py is re-run and the residual N is recorded
    in this ticket -- the count is the acceptance, not the exit code
  evidence: []
- text: given the COV and TEST finding sets captured before the sweep, when it completes,
    then the sets are byte-for-byte identical and the empty diff is pasted into the
    done-report
  evidence: []
- text: given the landed sweep, when agents review per package, then each condenses
    the relocated prose in its package and confirms paragraph 1 still reads as a utility
    summary for every symbol touched
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The execution leaf for the docstring half: once the fix exists (T-4807), run it
REPO-WIDE in a coordinator-declared quiet window, as ONE cross-ticket land.

WHY ONE LAND AND NOT EIGHT CLUSTERS. The comment-run work is clustered because it
is a judgement per block that agents make by hand. This is the opposite shape:
the fix is mechanical and the only safe way to apply 1,055 of them is all at once
against a still tree. Interleaving a 1,055-file mechanical rewrite with the
fleet's normal lands would collide with every open lease in the repo and make
every concurrent agent's `git diff` unreadable. Hence: a quiet window the
coordinator declares, not a ticket an agent picks up off the queue.

PRECONDITIONS, all of them hard:
- T-4807 landed, its idempotency and refuse-on-missing-ticket acceptance proven.
- A coordinator-declared quiet window: no in-progress lands, and the fleet told
  in advance. Dirty root DirtyMain-blocks everyone, and this land touches most of
  `src/frob`.
- A lease/scope check first: this is explicitly a CROSS-TICKET land. Enumerate
  what is leased at the moment the window opens and land with the cross-ticket
  allowance the coordinator uses, rather than discovering the collision at the
  refusal.
- `frob ticket list` exits 0 after every batch, not just at the end. 1,055 body
  appends against a ledger where most cited tickets are ARCHIVED is exactly the
  DuplicateId shape that previously downed every ledger load repo-wide (T-2994
  constraint 3). Batch it, and check between batches.

ACCEPTANCE IS THE COUNT. Measured today: 1,055 docstrings over 20 lines, 38,964
lines (scratchpad/struct.py). After the sweep, re-run that same script and record
the residual N in this ticket. "The fix ran and exited 0" is not the acceptance;
the wrapper's exit code is not the work. N is.

AGENTS REVIEW DIFFS PER PACKAGE. The mechanical application is one land, but the
REVIEW is split per package -- the same package boundaries the cluster leaves use
(gates/, tickets/, app/ticket_runner/, graph/, lang/, strata/, and the tail).
Each reviewing agent CONDENSES the relocated prose in its package rather than
re-authoring the moves, and confirms paragraph 1 still reads as a utility summary
for every symbol it touched. That review is where T-2994's judgement actually
happens for the docstring half.

THE CHECK THAT CATCHES A SILENT DISASTER: the COV and TEST finding sets must be
byte-for-byte identical before and after. Docstrings feed COV002 and the
frob:doc edges feed DRIFT001/COV001; a sweep that shifts the finding set by one
entry has moved the enforcement surface, not just prose. Capture both sets, diff
them, and paste the diff (expected: empty) into the done-report.
