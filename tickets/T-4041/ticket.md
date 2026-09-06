---
id: T-4041
title: frob verify now drains debt but dirties the primary with an unattributed lock-file
  rewrite, creating new ledger debt
state: queued
kind: bug
origin: human
created: '2026-09-06'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/verify_runner.py
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
Consumer apollo, 2026-09-06:

  "`frob verify now` drains deferred verification debt and advances the
   watermark; doing so REWRITES frob-coverage.lock.json on the primary, which
   then needs its own attribution micro-ticket (T-0122 pattern)."

A MAINTENANCE COMMAND THAT CREATES LEDGER DEBT BY RUNNING. The verb whose entire
purpose is to DRAIN deferred debt leaves behind a modified tracked file on the
primary checkout, and that modification then requires its own ticket to attribute
and land. Draining debt manufactures debt.

WHY THIS IS A DESIGN DEFECT AND NOT A CHORE. Every other tracked-file mutation
frob performs during normal operation is attributed automatically -- scope
mirrors, evidence, done-reports and changelog fragments all land under the ticket
whose work caused them. This one is not, so the user is left holding a dirty
primary and must invent a ticket to explain a file frob itself rewrote for its
own bookkeeping. Worse, a dirty primary is exactly the condition that
DirtyMain-blocks other agents' lands, so the cost is not local to the person who
ran the command.

NOTE THE SHAPE, because it recurs: an operation is individually correct and
leaves residue that the surrounding system then treats as unaccounted work. This
repo has the same shape recorded for query commands writing ticket files into the
shared root, and for killed retry loops leaving untracked directories.

THREE CANDIDATE FIXES, in preference order. Determine which is right by
establishing WHO OWNS the lock file's content:
  1. ATTRIBUTE IT AUTOMATICALLY. If the rewrite is a deterministic consequence of
     draining verification debt, frob should commit it with a self-describing
     message, the way the ledger auto-commit already handles its own writes. No
     ticket needed because no human decision is involved.
  2. DO NOT WRITE IT ON THE PRIMARY. If the watermark is per-run bookkeeping
     rather than shared state, it may belong in .frob/ (already gitignored)
     rather than in a tracked lock file.
  3. If it genuinely IS shared state that a human should review, then say so at
     the moment of the write -- name the file and state that it needs
     attribution -- rather than leaving the user to discover a dirty primary.
DO NOT pick (3) by default. It is the current behaviour minus the surprise, and
the consumer's complaint is the work, not the surprise.

VERIFY FIRST: is frob-coverage.lock.json's content deterministic given the same
inputs? If two runs produce different bytes for the same underlying state, that
is a separate and worse defect (spurious diffs on every run) and changes which
fix is correct.

RELATED: T-4007 covers the profile auto-ratchet's missing durable record and its
possible effect on coverage stamping; both touch what the coverage lock/stamp
files are for and who writes them. Read them together before designing.

MUST-FIRE FIXTURE: running the drain verb leaves the primary checkout CLEAN, or
leaves an auto-attributed commit -- not an unexplained dirty tracked file.
MUST-STAY-QUIET: the watermark still advances and the debt is still drained; the
fix must not achieve cleanliness by not doing the work.

ACCEPTANCE
- Ownership of the lock file's content established, and the fix chosen from it.
- Determinism of its content verified.
- No unattributed dirty primary after the command.
- Both fixtures committed.