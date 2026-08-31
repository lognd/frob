---
id: T-3564
title: Wire the tests-first-then-implementation land splice into the live land path
  (T-3546 design)
state: queued
kind: feature
origin: agent
created: '2026-08-31'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land_squash.py
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
Implementation half of T-3546's design (docs/design/land-splice-test-then-impl.md). T-3546 landed the design plus the UNWIRED mechanical primitives (classify_test_then_impl_paths/compose_test_then_impl_commits in src/frob/tickets/_land_squash.py, proven against a scratch repo in tests/unit/test_land_splice_test_then_impl.py) but does NOT call them from the live land path -- _fold_publish_and_resync/_publish_squash_apply still compose a single squash commit via fold_worktree_into_commit, unchanged. This ticket wires the split in: when classify_test_then_impl_paths returns a real split for the disposable stage's changed-path set, call compose_test_then_impl_commits instead of fold_worktree_into_commit and publish_ref_cas straight to the SECOND commit's sha (never the first -- see the design doc's 'Why this is safe' section for why this keeps the CAS race semantics byte-for-byte identical to today). When classify_test_then_impl_paths returns None, fall back to today's single-squash path unchanged. Also implement the design's Consequence 1 (--check-repro post-land verifiability via derive_land_commit_by_grep-style dual-match resolution) and Consequence 2 (Land-Splice-Role commit trailers + a docs/guides/ bisect-skip recipe). This is T-3053's highest-incident-density code path (T-3066/T-3114/T-3121/T-3163 all root-caused in this function family) -- land incrementally, behind extensive scratch-repo test coverage before touching _fold_publish_and_resync itself, and get the design doc's own consequences re-verified against the actual implementation before wiring the call site. BLOCKED on T-3546's design doc receiving owner sign-off (T-3550 precedent).