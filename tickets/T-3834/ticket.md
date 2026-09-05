---
id: T-3834
title: 'F-029: frob coverage --full defaults to --cov=src/frob when pyproject has
  no [tool.coverage.run] source -- misleading RED'
state: queued
kind: bug
origin: human
created: '2026-09-05'
priority: medium
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
body_changes:
- mode: append
  reason: consumer re-reported this as F-119; verified it is not a recurrence but
    this filed ticket unworked, with the hardcoded site and its own self-documenting
    docstring named
  actor: logan
  at: '2026-09-05'
  old_length: 0
  new_length: 2638
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---

RE-REPORTED BY THE SAME CONSUMER, 2026-09-05, as logand.app-v2 F-119, which
labels it "F-029 recurrence". IT IS NOT A RECURRENCE -- IT IS THIS TICKET,
FILED AND NEVER WORKED. Verified on main just now:

    src/frob/testing/_coverage_refresh.py:110
        _DEFAULT_COV_TARGET = "src/frob"
    src/frob/testing/_coverage_refresh.py:96
        #: coverage recipe measures (mirrors `Makefile`'s `--cov=src/frob`)
    src/frob/testing/_coverage_refresh.py:121
        ... instead of this module's own hardcoded "src/frob" ...

THE MODULE'S OWN DOCSTRING NAMES THE DEFECT. Line 121 already describes
resolving the real package instead of the hardcoded value, so the correct
behaviour was understood at the time of writing and not implemented.

THREE THINGS THIS CHANGES ABOUT THE TICKET'S PRIORITY:

  1. IT IS A CONSUMER-BLOCKING PORTABILITY BUG, not a frob-internal nicety. In
     THIS repo `src/frob` is correct, so it is invisible here forever. In any
     other repo `frob coverage --full` measures a directory that does not
     exist and reports a misleading RED. The consumer has now hit it twice and
     told us twice.
  2. THE OWNER ASKED ABOUT THIS EXACT DEFECT IN A PRIOR SESSION -- "frob
     coverage hardcodes src/frob; how is our dogfooding not catching that?" The
     answer then was that PORT001 scans only detector packages, so frob's own
     dogfooding is STRUCTURALLY BLIND to it. That answer is still true, which
     means nothing in this repo will ever surface it and only consumer reports
     can.
  3. A RE-REPORT IS ITSELF A SIGNAL ABOUT PRIORITISATION, not just about the
     bug. When a consumer files the same friction twice, the queue is not
     draining what they actually hit. Worth noting alongside F-081 (nothing
     detects a ticket whose premise has expired): this is the inverse case -- a
     ticket whose premise is emphatically still alive, sitting queued while
     newer work lands around it.

FIX SHAPE, unchanged from the original filing but now with the site named:
resolve the coverage target from the project's own configuration
([tool.coverage.run] source, or the discovered package) and fall back to the
hardcoded value only for frob itself -- or better, do not fall back at all and
REFUSE with a clear message naming what to configure, since a wrong default
here produces a misleading RED rather than an obvious failure.

RELATED, DO NOT FIX BLIND: memory records that 22 files hardcode `src/frob/`.
This is one of them. Fixing this site alone leaves the class; check whether the
other 21 are the same shape before scoping, and say whether this ticket covers
one site or the class.
