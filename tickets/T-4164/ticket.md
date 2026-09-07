---
id: T-4164
title: frob ticket sprint assign mutates the ledger, reports success and never commits,
  leaving the shared root dirty and blocking every agent land
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
- src/frob/app/ticket_runner/_mutate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given a sprint assignment, when the verb returns success, then the working
    tree is clean and the change is committed
  evidence: []
- text: given the no-commit escape hatch, when the verb returns, then the change is
    written uncommitted and the caller is warned the ledger is left dirty
  evidence: []
- text: given every ticket verb that mutates the ledger, when each returns success,
    then none leaves an uncommitted write
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
`frob ticket sprint assign` MUTATES THE LEDGER, REPORTS SUCCESS, AND NEVER
COMMITS -- leaving the shared checkout dirty, which DirtyMain-blocks every agent's
land until someone notices.

MEASURED IN src/frob/app/ticket_runner/_mutate.py:1109. The whole body is:

    result = set_sprint(root, cfg.ticket_id, cfg.ticket_sprint)
    if result.is_err: ... sys.exit(1)
    _log.info("%s sprint set to %s", ...)

It writes and returns. There is no commit, and -- unlike every sibling ledger
verb -- its parser carries no `--no-commit` flag either, which is itself the tell:
`new`, `drop`, `fail`, `block`, `scope` and `body` all expose that flag precisely
because they DO auto-commit by default (T-1615's uniform behaviour, T-1130's
precedent). This verb was left out of that migration and nothing noticed, because
its output says the work succeeded.

I HIT THIS TWICE TODAY AS THE COORDINATOR. Both times the verb printed
"T-XXXX sprint set to alpha-gate" and both times the shared root was left dirty
with the modified ticket file. I only caught it because I run a fleet status check
each cycle; the message gave no hint. A dirty shared root blocks EVERY concurrent
agent land, so a verb that quietly dirties it converts a bookkeeping call into a
fleet-wide stall with nothing naming the cause. This repo has already recorded
that exact chain from a different source.

THERE IS A WORSE SECOND-ORDER OUTCOME AND IT SHOULD BE CHECKED, NOT ASSUMED.
Earlier in the same session I assigned six tickets to a sprint in one loop, and
the root read clean afterwards. I did not commit those. Something else did --
almost certainly a concurrent land sweeping a bystander's dirty file into its own
commit. This repo carries a test named for exactly that hazard
(`test_record_land_commit_never_absorbs_a_bystanders_dirty_file`), so the
protection is supposed to exist. DETERMINE WHAT ACTUALLY HAPPENED to those six
ledger edits: whether they were absorbed into an unrelated ticket's land commit,
committed by a later verb's own auto-commit, or something else. If a land did
absorb them, that is a second defect and a more serious one than this ticket.

WHAT TO DO
  1. Give this verb the same uniform auto-commit its siblings have, with the same
     `--no-commit` escape hatch, so the family is consistent.
  2. Audit the rest of the ticket verb surface for other non-committing mutators.
     The absent flag is a cheap detector: any verb that mutates the ledger and
     does NOT expose `--no-commit` is a candidate. Report the list.
  3. Consider a guard rather than a per-verb fix: a mutating verb that returns
     while its own ledger write is uncommitted could refuse or warn loudly. That
     turns the whole class into one check instead of N corrections.
  4. Resolve the six-edit question above and file separately if a land absorbed
     them.

MUST-FIRE FIXTURE:   assigning a sprint leaves the working tree clean and the
                     change committed.
MUST-STAY-QUIET:     with the no-commit escape hatch, the change is written and
                     NOT committed, and the caller is warned that the ledger is
                     left dirty -- matching the sibling verbs' existing wording.
THIRD FIXTURE:       no ticket verb that mutates the ledger returns success with
                     an uncommitted write, proven across the verb surface rather
                     than for this one verb.

ACCEPTANCE
- The verb auto-commits, with the standard escape hatch.
- The rest of the mutating verb surface audited, with any siblings named.
- The fate of the six earlier uncommitted edits determined and recorded.
- All three fixtures committed.
