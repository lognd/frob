---
id: T-2595
title: Lock or CAS-write .frob/rapid-sweep-baseline.json against concurrent detached-sweep
  writers
state: done
kind: bug
origin: human
created: '2026-08-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_rapid_sweep.py
- tests/unit/test_rapid_sweep.py
evidence_scope:
- tests/unit/test_rapid_sweep.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_rapid_sweep.py
  reason: the repro tests and CAS/lock unit coverage live here
  actor: logan
  at: '2026-08-19'
evidence:
- tests/unit/test_rapid_sweep.py::TestDeferredSweepBaselineCasRace::test_a_sweep_computed_against_a_stale_tree_does_not_clobber_a_fresher_ones_baseline
- tests/unit/test_rapid_sweep.py::TestBaselineLock::test_no_lock_primitive_refuses_loudly
- tests/unit/test_rapid_sweep.py::TestBaselineLock::test_serializes_two_concurrent_holders
- tests/unit/test_rapid_sweep.py::TestIsAncestor::test_true_when_older_is_ancestor
- tests/unit/test_rapid_sweep.py::TestIsAncestor::test_equal_commits_are_ancestors
- tests/unit/test_rapid_sweep.py::TestIsAncestor::test_false_when_not_an_ancestor
- tests/unit/test_rapid_sweep.py::TestIsAncestor::test_none_on_git_failure
- tests/unit/test_rapid_sweep.py::TestWriteBaselineCas::test_writes_when_no_prior_baseline
- tests/unit/test_rapid_sweep.py::TestWriteBaselineCas::test_writes_when_prior_is_an_ancestor
- tests/unit/test_rapid_sweep.py::TestWriteBaselineCas::test_skips_when_prior_is_not_an_ancestor
- tests/unit/test_rapid_sweep.py::TestWriteBaselineCas::test_writes_when_ancestry_is_unresolvable
designated_repro_test: tests/unit/test_rapid_sweep.py::TestDeferredSweepBaselineCasRace::test_a_sweep_computed_against_a_stale_tree_does_not_clobber_a_fresher_ones_baseline
evidence_changes:
- old_node: tests/unit/test_rapid_sweep.py::TestBaselineLock::test_no_fcntl_degrades_to_unlocked
  new_node: tests/unit/test_rapid_sweep.py::TestBaselineLock::test_no_lock_primitive_refuses_loudly
  reason: 'T-2918: fcntl-absent path no longer silently proceeds unlocked -- it raises
    BaselineLockUnavailable; test_no_fcntl_degrades_to_unlocked no longer describes
    real behavior and was replaced by test_no_lock_primitive_refuses_loudly'
  actor: logan
  at: '2026-08-25'
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: a1d9b9d48dac5e8331918518ebfae4f922e34796
---
T-2571 fixed two defect classes behind the deferred post-land sweep's
false-positive regression filings: phantom findings against a
land-deleted file (fixed), and detecting -- but not preventing -- a
concurrent-sweep clobber of .frob/rapid-sweep-baseline.json.

The rolling baseline file lives at the shared checkout root (T-1684 by
design: every land's own detached, off-critical-path sweep operates
against the SAME root), and concurrent lands routinely spawn concurrent
sweeps in this fleet. Two sweeps can race: sweep B reads the baseline
before sweep A's write lands, computes its own new_findings diff against
a baseline that is already stale, and B's own subsequent write can in
turn discard whatever A just recorded. T-2571's own
_baseline_write_survived makes this race DETECTABLE (logs a WARNING
naming the sweep/commit when a write does not survive) but does not
prevent it -- the plausible mechanism behind an identical (rule, file)
identity set recurring as "new" across 3+ consecutive, otherwise
unrelated sweeps (measured across T-2381/T-2474/T-2525/T-2560).

Fix the race itself: either a file lock (flock, matching land.lock's own
posture) around the read-modify-write of
.frob/rapid-sweep-baseline.json, or a compare-and-swap write (read the
current commit, write only if it still matches what this sweep read
before computing fresh, else re-read-merge-retry). Either approach must
not turn concurrent sweeps into a serialization bottleneck (rapid's
whole point is staying off the land critical path, T-1684) -- a lock
held only for the tiny read+write itself, not the multi-minute frob
check in between, is the shape to aim for.