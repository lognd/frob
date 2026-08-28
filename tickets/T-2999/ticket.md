---
id: T-2999
title: 'Baseline lock files: staleness warning, and a LOUD failure when the producer
  that stamps them stops running'
state: queued
kind: bug
origin: human
created: '2026-08-26'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_lock_producer.py
- src/frob/app/status_runner.py
- tests/unit/gates/test_lock_producer.py
- src/frob/gates/_coverage.py
- docs/modules/cli.md
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_lock_producer.py
  reason: shared producer-staleness helper + frob status wiring + one concrete LOUD-failure
    wire-up (coverage lock, the best-established of the three) with must-fire/must-stay-quiet
    coverage
  actor: logan
  at: '2026-08-28'
- op: add
  glob: src/frob/app/status_runner.py
  reason: shared producer-staleness helper + frob status wiring + one concrete LOUD-failure
    wire-up (coverage lock, the best-established of the three) with must-fire/must-stay-quiet
    coverage
  actor: logan
  at: '2026-08-28'
- op: add
  glob: tests/unit/gates/test_lock_producer.py
  reason: shared producer-staleness helper + frob status wiring + one concrete LOUD-failure
    wire-up (coverage lock, the best-established of the three) with must-fire/must-stay-quiet
    coverage
  actor: logan
  at: '2026-08-28'
- op: add
  glob: src/frob/gates/_coverage.py
  reason: shared producer-staleness helper + frob status wiring + one concrete LOUD-failure
    wire-up (coverage lock, the best-established of the three) with must-fire/must-stay-quiet
    coverage
  actor: logan
  at: '2026-08-28'
- op: add
  glob: docs/modules/status.md
  reason: shared producer-staleness helper + frob status wiring + one concrete LOUD-failure
    wire-up (coverage lock, the best-established of the three) with must-fire/must-stay-quiet
    coverage
  actor: logan
  at: '2026-08-28'
- op: remove
  glob: docs/modules/status.md
  reason: match existing frob:doc anchors for status_runner.py/_coverage.py rather
    than a nonexistent docs/modules/status.md
  actor: logan
  at: '2026-08-28'
- op: add
  glob: docs/modules/cli.md
  reason: match existing frob:doc anchors for status_runner.py/_coverage.py rather
    than a nonexistent docs/modules/status.md
  actor: logan
  at: '2026-08-28'
- op: add
  glob: docs/modules/gates.md
  reason: match existing frob:doc anchors for status_runner.py/_coverage.py rather
    than a nonexistent docs/modules/status.md
  actor: logan
  at: '2026-08-28'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
OWNER DECISION (2026-08-26): the `.lock.json` baselines should carry a staleness
warning -- AND, the part that matters most, the failure mode where their
PRODUCER STOPS RUNNING must be LOUD.

THE PROBLEM. Three tracked baselines sit in the repo root:

    frob-coverage.lock.json             20,847 B   last touched 2026-08-06 (20d)
    frob-deprecated-baseline.lock.json   7,230 B   last touched 2026-07-28 (29d)
    frob-ratchet.lock.json               3,119 B   last touched 2026-07-23 (34d)

From the outside, two completely different states look IDENTICAL:

  (a) the baseline is deliberately frozen and old because nothing has needed to
      move it -- correct and healthy;
  (b) the producer that stamps it stopped running weeks ago, so the baseline is
      a fossil that every downstream consumer is silently trusting as current.

State (b) is the dangerous one and it is invisible today. A stale baseline does
not fail; it quietly answers questions with old data. This repo has already paid
for exactly this shape: a 53-commit-stale verification watermark caused the
post-land sweep to file three phantom regression tickets against pre-existing
findings, which is what T-2929 was written to stop.

Note `frob-coverage.lock.json` specifically: its last commit was a FIX to
coverage handling, not a refresh. So the evidence points at (b) -- the coverage
refresh has probably not run in 20 days -- but nothing in the system says so.

WHAT IS WANTED, two parts, and the second is the real requirement:

1. A staleness WARNING surfaced where an operator already looks -- `frob status`
   is the natural home (it already reports verification lag and refuses to print
   a delta against a stale baseline). Report each baseline's age and what last
   stamped it, so (a) and (b) become distinguishable by reading rather than by
   archaeology.

2. LOUD FAILURE WHEN THE PRODUCER STOPS. A warning that a baseline is old is not
   enough on its own, because a legitimately-frozen baseline is also old and the
   two warnings read the same. What must be loud is the PRODUCER having stopped:
   the thing that stamps this baseline has not run in N runs / N days despite
   conditions where it should have.

   Design the detection around the producer, not the artifact age. Candidate
   signals, to be validated rather than assumed: the baseline's recorded stamp
   commit is far behind HEAD while the code it baselines has changed; the
   producer's own last-run record (if one exists) is absent or ancient; a
   consumer reads the baseline and finds its keys no longer correspond to
   anything in the current tree.

   Follow this repo's established doctrine rather than inventing a new one:
   `frob verify` REFUSES to attribute against a stale baseline (T-2929) and gate
   results render `UNRES` rather than `pass` when unmeasured (T-2891). A
   consumer reading a baseline whose producer has stopped should behave the same
   way -- report UNMEASURED, not a confident answer from fossil data. An honest
   "I do not know" beats a comfortable wrong number, which is the most repeated
   lesson of this drive.

DISTINGUISH DELIBERATE FREEZE FROM ABANDONMENT. A baseline that is intentionally
pinned must have a way to say so, so it does not generate a permanent warning
that everyone learns to ignore -- a warning nobody can action is how real
signals get trained out. Whatever form that takes (an explicit pin field with a
reason, per the repo's waiver convention), it must be a positive declaration,
not silence.

ACCEPTANCE
- Each baseline's age and last-stamping producer are visible in `frob status`.
- A baseline whose producer has demonstrably stopped produces a LOUD, named
  failure or an explicit UNMEASURED result at the point of consumption -- not a
  silent stale answer. Must-fire fixture required.
- A deliberately-pinned baseline does NOT produce that failure, and its pin
  carries a stated reason. Must-stay-quiet fixture required.
- Report, for each of the three current baselines, which state it is actually in
  -- frozen-on-purpose or producer-stopped. That determination is part of this
  ticket, not a follow-up: if coverage genuinely has not been stamped in 20
  days, say so and file the fix.
