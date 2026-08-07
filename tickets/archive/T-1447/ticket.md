---
id: T-1447
title: T-1420 delivered portion 3
state: dropped
kind: feature
origin: human
created: '2026-08-02'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_reporting.py
- src/frob/tickets/_reporting_attachments.py
- src/frob/vet/_scan.py
- src/frob/vet/_scan_violations.py
- docs/modules/tickets.md
- tests/test_tickets.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
T-1420 delivered portion 3 of the LARGE001 residue burndown (WAVE4-L, this
worktree). Continues from portions 1/2 (T-1441/T-1442) with two more
verbatim-relocation splits:

1. src/frob/tickets/_reporting.py (845 -> 754 lines): the attach()/
   attachment-write quartet (attach, _attachment_bytes,
   _next_attachment_path, _record_attachment) moved verbatim to a new
   src/frob/tickets/_reporting_attachments.py -- the one filesystem-I/O
   concern in the former module, distinct from the done-report/review/drop
   prose-mutation family that stays behind. Re-exported from _reporting.py
   for existing callers. Repointed the frob:describes doc edge
   (docs/modules/tickets.md) and the frob:tests directive
   (tests/test_tickets.py) that named the old location.

2. src/frob/vet/_scan.py (915 -> 765 lines): the per-rule Violation
   constructor family (_vet001/002/003/004/006/011_violation,
   _quarantine_violation, _lockfile_name) moved verbatim to a new
   src/frob/vet/_scan_violations.py -- pure "decide and format one
   Violation" leaves with no I/O, distinct from _scan.py's own
   orchestration (locate source, run the scan, thread results through the
   parallel/sequential dependency loop). Re-exported for existing callers.
   No cross-file frob:tests/frob:describes directives named the old
   symbol locations (grepped clean before and after).

Waiver carries: grepped both source files for `frob:waive` BEFORE moving
anything, per the T-1420 brief's portion-2 lesson (INV006/PII012 carries
missed there). Neither _reporting.py's attachment quartet nor _scan.py's
violation-constructor block carried a directly-attached frob:waive of
their own (the file-level waivers in both source files stayed with the
functions that motivated them, none of which moved). Split #2 did surface
one PRE-EXISTING, previously-unwaived INV006 finding on _scan.py itself
(two 'only' hits in unrelated design prose -- a waiver-reason string and a
log message -- both present on main before this ticket touched the file);
disposed with a new frob:waive INV006 in _scan.py rather than left for the
next agent to rediscover, since it is inside this ticket's own declared
scope.

Neither split touches src/frob/tickets/_models.py, _store.py,
_new_renumber.py, src/frob/vet/_capability.py, or the two strata-core Rust
files still on T-1420's list -- those remain for a future portion. Scope
was narrowed from src/** to the exact remaining LARGE001 target list (plus
tests/**, docs/**) before starting, and re-narrowed after the tickets.md
main-restore step reverted it (section 10b's known first-ticket-per-
worktree edge case).

frob check --only archgate --only wire --only dead_symbols --only drift
--only doclink --only invariant --only pii_structural --only fmt --ticket
T-1420 is clean (0 errors) after both splits; LARGE001 warning count
dropped from 49 (session start baseline) to 47.

## Drop reason
- 2026-08-02: refiling with --parent T-1420