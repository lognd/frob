---
id: T-3618
title: 'TDD001 per-edge git-log walk is unbudgeted: ~200-300s/edge makes large lands
  structurally unlandable'
state: in-progress
kind: bug
origin: agent
created: '2026-08-31'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_tdd_order.py
- src/frob/tickets/_land.py
- tests/gates/test_tdd_order.py
- tests/test_ticket_land.py
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_tdd_order.py
  reason: TDD001 perf fix touches the check module, its land call site, and both test
    files
  actor: logan
  at: '2026-08-31'
- op: add
  glob: src/frob/tickets/_land.py
  reason: TDD001 perf fix touches the check module, its land call site, and both test
    files
  actor: logan
  at: '2026-08-31'
- op: add
  glob: tests/gates/test_tdd_order.py
  reason: TDD001 perf fix touches the check module, its land call site, and both test
    files
  actor: logan
  at: '2026-08-31'
- op: add
  glob: tests/test_ticket_land.py
  reason: TDD001 perf fix touches the check module, its land call site, and both test
    files
  actor: logan
  at: '2026-08-31'
- op: add
  glob: docs/modules/gates.md
  reason: AFFECT001 requires touching the tdd001-t-3009 doc anchor since resolve_symbol_introduction/tdd_order_violations
    changed
  actor: logan
  at: '2026-08-31'
evidence:
- tests/gates/test_tdd_order.py::TestPerfShape::test_since_bounds_the_log_walk_to_a_revision_range
- tests/gates/test_tdd_order.py::TestPerfShape::test_shared_file_is_walked_and_read_exactly_once_across_edges
- tests/test_ticket_land.py::TestCheckTddOrder::test_passes_the_resolved_merge_base_as_since
- tests/test_ticket_land.py::TestCheckTddOrder::test_falls_back_to_unbounded_when_merge_base_is_unresolvable
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
TDD001's land-time diff-scoped per-edge check runs an unbudgeted git-log
history walk per evidence edge. Measured (T-3586's land, 17 attempts,
2026-09-01): ~200-300s PER EDGE against a file with a long history
(src/frob/gates/__init__.py), at both high (load 7.6) and low (load 2.8)
host contention -- the scan got through only 1-3 edges per 595s window
every time. A 14-file split land has enough edges that the land needs
50-150 minutes of TDD001 alone, which no foreground shell can hold: the
landing agent killed its own land 17 times via its timeout wrapper, and
the coordinator's hook demands a 540s wrapper. The land is structurally
unlandable until this is fixed.

Fix directions (implementer chooses, measured result decides):
1. Bound the git-log walk: the check needs test-before-impl ORDER for
   the edge's commits -- limit the walk with pathspec pairs and
   --max-count / a merge-base horizon instead of full history; the land
   only needs commits since the worktree's merge-base with main, not
   all time.
2. Batch: one git log over the union of edge paths, bucketed per edge
   afterward, instead of N separate walks over overlapping history.
3. Memoize per (path, head) within one land invocation -- repeated
   edges against the same file (measured: multiple edges on
   gates/__init__.py) must not re-walk.
4. If a hard time budget is added as a backstop, it must be LOUD
   (per-edge SKIPPED-with-reason surfaced in the land output and the
   check summary), never a silent pass -- budget reduces coverage, not
   time, and silent zeros are the repo's dominant bug class.

Acceptance: a land of the t-3586 worktree (14-file split) completes its
TDD001 phase in under 120s total. Add a perf regression test pinning
the per-edge cost shape (e.g. call-count/pathspec assertions on the git
invocations, not wall-clock).

NOTE: the t-3586 worktree contains a worktree-local draft
(T-draft-aa45924e, tip commit a9a8ba61e) documenting the same bug with
scope src/frob/tickets/_land.py + src/frob/gates/_tdd_order.py -- it
will promote to a real id when t-3586 lands. After THIS ticket lands,
whoever lands t-3586 should drop/merge that draft as a duplicate rather
than leaving two open tickets for one bug.
