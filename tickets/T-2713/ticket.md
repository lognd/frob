---
id: T-2713
title: Deferred verification advances the watermark and records the rolling baseline
  from a budget-truncated check (saw 2 of 40 error identities, called it GREEN)
state: queued
kind: bug
origin: human
created: '2026-08-20'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
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
## Measured, 2026-08-20

`frob verify now` drained a 3-entry queue (54 commits behind the
watermark). It spawned:

    ['.venv/bin/python', '-m', 'frob', 'check', '--budget', '480', '--json']

and then:

    rapid sweep: recorded rolling baseline of 2 error(s) at 970a4a6a08af
    verify worker: GREEN at 970a4a6a08af (2 error(s)) -- watermark advanced,
    3 queue entr(y/ies) compacted
    advanced watermark: True

`.frob/rapid-sweep-baseline.json` after the run contains exactly two
findings:

    [["CLAUDE001", ".claude/hooks/sync-claude-config.py"],
     ["CYCLE001",  "src/frob/__init__.py"]]

An UNBUDGETED `frob check --json` on the same tree, taken minutes later,
reports:

    severity counts: {'warning': 1671, 'error': 65, 'info': 93, 'note': 1399}
    distinct error identities: 40

So the verification saw 2 of 40 error identities and called it GREEN.

## Two independent failures, both severe

1. FALSE GREEN ON 54 COMMITS. The watermark advanced through
   970a4a6a08af and the queue was compacted, marking every commit since
   the previous watermark as verified. Nothing re-examines them. A budget
   REDUCES COVERAGE rather than shortening runtime -- it drops whole gate
   families -- so "green under budget" is not evidence of green, it is an
   unmeasured result rendered as a clean one. That is the silent-zero
   doctrine violated by the very machinery meant to enforce it.

2. THE ROLLING BASELINE IS POISONED, AND THIS IS THE LONG-SOUGHT ROOT
   CAUSE OF THE FALSE-REGRESSION TICKETS. The baseline now records 2
   identities against a tree that genuinely has 40. The next post-land
   sweep compares against it and will see ~38 PRE-EXISTING findings as
   NEW, and file them as a regression ticket against whichever land runs
   next.

   This matches the observed history exactly: T-2381 (27 identities),
   T-2474 (39), T-2525 (38), T-2560 (38) -- all filed as "new from this
   land", all triaged and DROPPED as false. Prior tickets attributed this
   to a stale/unlocked baseline file (T-2595) or to phantom deleted paths
   (T-2571). Those were real but partial. A budget-truncated baseline
   explains the SIZE and the RECURRENCE in a way neither does: every
   budgeted verification rewrites the baseline with a fraction of the
   true finding set, so the next sweep's diff is enormous and almost
   entirely false.

## Required

- A verification that could not measure the full gate set MUST NOT
  advance the watermark and MUST NOT record a baseline. Refusing to
  advance is correct; rendering an unmeasured run as GREEN is not.
- If a budget is needed for runtime, the run must be reported as
  PARTIAL/UNMEASURED and the watermark left where it is, exactly as
  `frob ticket close` already refuses to close on an unparsable
  gate-summary.
- The baseline write must be gated on a complete measurement.

## Positive controls, both directions

- a budget-truncated verification does NOT advance the watermark and does
  NOT overwrite the baseline
- a complete verification DOES advance it and DOES record a baseline
  whose identity count matches an independent unbudgeted `frob check`
- a genuinely green complete run still reports green (do not fix this by
  refusing to ever advance)

## Note for whoever picks this up

Re-measure before trusting these numbers -- lands are ongoing and the
floor moves. The METHOD is the durable part: compare
`.frob/rapid-sweep-baseline.json`'s finding count against an unbudgeted
`frob check --json` piped through `scripts/check_summary.py` on the same
commit. A large gap is the bug.
