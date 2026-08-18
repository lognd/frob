---
id: T-2324
title: 'The wired drain runs to completion and never advances the watermark: advance-only-on-green
  cannot drain a backlog that is never fully green'
state: done
kind: bug
origin: agent
created: '2026-08-17'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/verify/_worker.py
- src/frob/verify/_drain.py
- tests/unit/verify/test_worker.py
- docs/modules/tickets-verify-sweep.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/verify/_worker.py
  reason: 'T-2324 fix: red-but-owned findings advance the watermark'
  actor: logan
  at: '2026-08-17'
- op: add
  glob: src/frob/verify/_drain.py
  reason: 'T-2324 fix: red-but-owned findings advance the watermark'
  actor: logan
  at: '2026-08-17'
- op: add
  glob: tests/unit/verify/test_worker.py
  reason: 'T-2324 fix: red-but-owned findings advance the watermark'
  actor: logan
  at: '2026-08-17'
- op: add
  glob: docs/modules/tickets-verify-sweep.md
  reason: 'T-2324 fix: red-but-owned findings advance the watermark'
  actor: logan
  at: '2026-08-17'
evidence:
- tests/unit/verify/test_worker.py::TestRunCoalescedVerification::test_new_findings_filed_to_a_real_ticket_still_advance
- tests/unit/verify/test_worker.py::TestRunCoalescedVerification::test_new_findings_that_cannot_be_filed_still_do_not_advance
designated_repro_test: null
acceptance:
- text: given a backlog whose commits include findings, when the drain runs, then
    the watermark advances past the verified prefix rather than staying put
  evidence:
  - tests/unit/verify/test_worker.py::TestRunCoalescedVerification::test_new_findings_filed_to_a_real_ticket_still_advance
- text: given a commit carrying an unattributed finding, when the drain runs, then
    that commit is not silently certified as verified
  evidence:
  - tests/unit/verify/test_worker.py::TestRunCoalescedVerification::test_new_findings_that_cannot_be_filed_still_do_not_advance
- text: given this repo's real multi-hundred-commit backlog, when the drain runs repeatedly,
    then commits-since-watermark trends down rather than up
  evidence:
  - tests/unit/verify/test_worker.py::TestRunCoalescedVerification::test_new_findings_filed_to_a_real_ticket_still_advance
threat: null
component: verify
anchor: false
anchor_reason: null
land_commit: 30d238be4585a661d0e9f0954cfa4035cc4b7d89
---
MEASURED 2026-08-17, immediately after T-2317 wired the drain.

T-2310 built the drain and T-2317 wired it into the rapid-land path. Both
work: a land spawns `frob verify drain-async`, the detached process starts,
runs, and exits cleanly. Verified directly.

    before drain:  watermark f0ab85d0, commits since watermark 567
    drain runs:    ~3.5 minutes, process observed alive then exited
    after drain:   watermark f0ab85d0, commits since watermark 570

THE WATERMARK DID NOT MOVE. The gap GREW, because lands kept arriving while
the drain ran.

LIKELY MECHANISM (determine this FIRST, do not assume): `run_coalesced_
verification`'s pre-existing contract is "verify once, advance only on
GREEN, leave the watermark untouched on red or unmeasurable" -- quoted from
T-2310's own implementation notes. If the coalesced verification of a
570-commit backlog reports ANY finding, the watermark stays put. This repo
has a non-zero error floor essentially always, so on that reading the drain
can never advance and the debt is unbounded regardless of how often it runs.

FIRST TASK: establish whether the drain came back RED or UNMEASURABLE, and
say which. Run the drain in the foreground and capture its verdict rather
than inferring it. The two cases need different fixes and guessing wrong
wastes the pass.

WHY ADVANCE-ONLY-ON-GREEN IS THE WRONG CONTRACT AT DEPTH: it is sound for a
one-commit step (do not certify a commit you could not verify). It is
unsound as a backlog drain, because it makes progress conditional on the
ENTIRE backlog being clean at once, which is strictly harder the further
behind you fall. The mechanism is self-defeating exactly when it is most
needed.

FIX DIRECTIONS (choose after measuring; this is a design decision, so if the
right answer is not one of these, STOP and report rather than guessing):
 (a) Advance the watermark PAST commits whose findings are already
     attributed to an owning ticket. A finding with an owner is accounted
     for -- that is what the ticket system is for -- so it should not
     also pin the watermark forever.
 (b) Advance incrementally to the last GREEN prefix rather than
     all-or-nothing, so a red commit in the middle stops progress at that
     point instead of discarding the whole pass.
 (c) Separate "verified clean" from "verified, findings recorded". The
     watermark's job is to mark how far verification has REACHED; a
     separate record can carry what it found. Conflating the two is what
     produces the deadlock.
(b) is the smallest change that restores forward progress; (a) composes
with the existing attribution engine; (c) is the most correct and the most
invasive.

HARD CONSTRAINT, INHERITED: whatever is built must NEVER block or delay a
land. Rapid's never-block contract holds. If a fix cannot preserve it,
report the conflict instead of relaxing it.

POSITIVE CONTROLS: (1) a backlog containing a red commit still advances the
watermark past the green prefix before it; (2) must-still-pass -- a commit
with an UNATTRIBUTED finding is NOT silently certified as verified;
(3) run against this repo's real 570-commit backlog, not a synthetic
two-commit gap -- the failure only appears at depth.