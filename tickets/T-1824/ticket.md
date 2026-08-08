---
id: T-1824
title: 'TEST011: add per-symbol deflation heuristic for partial xdist worker-crash
  merge loss'
state: queued
kind: feature
origin: human
created: '2026-08-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_coverage.py
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
Design and implement a per-symbol deflation heuristic in TEST011 distinct
from the existing aggregate module_join_fraction check. The aggregate
check stays silent when only a handful of symbols are affected by an
xdist worker crash but the overall repo-wide join fraction still looks
healthy, so a genuine per-symbol false 0.0% (def-line hit=1, every body
line hit=0, the exact shape reported by several agents against T-1353)
can slip through undetected even after T-1353's node-down-retry mitigation
lands.

Filed from T-1389's own investigation: a direct, controlled xdist repro
(-n 4, real branch/parallel/relative_files/sigterm settings matching
`make coverage`) against the originally-cited symbol
(src/frob/app/worktree_runner.py) did NOT reproduce a 0% false-negative
at that scale -- the coverage.xml combine/[paths] remap logic itself
looks sound. The likely explanation is T-1353's already-fixed node-down
class: a crashed worker under full-suite-scale load drops its entire
contribution, which can zero out just the handful of symbols that worker
happened to be the sole source of data for. T-1353's retry-on-node-down
fix (Makefile) reduces how often this happens but a still-imperfect merge
or a worker crash mid-retry could still slip a real false 0.0% through
undetected by the current TEST011 aggregate check.

Plan sketch:
- Add a per-symbol check to TEST011 (src/frob/gates/_coverage.py) that
  flags a symbol as suspect-deflated when its own defining line shows a
  hit but every subsequent body line in the same symbol shows 0 -- the
  specific shape distinguishing "genuinely never executed" from "worker
  lost mid-symbol data".
- Needs a way to distinguish this from a real, legitimately-dead code
  path (e.g. an unreachable branch) -- false positives here would be
  worse than the problem, since TEST005/TEST011 already gate real work.
  Consider requiring corroboration (a sibling test file that exercises
  the symbol per frob:tests edges, or historical coverage data via
  frob-coverage.lock.json's own ratchet) before flagging, not a bare
  per-line heuristic alone.
- Add a regression test with a synthetic coverage.xml fixture matching
  the def-line-hit/body-lines-0 shape.
