---
id: T-2290
title: 'rapid profile defers verification with no drain: watermark 6 days and 403
  commits stale, and reported unverified depth (84) understates it ~5x'
state: done
kind: bug
origin: agent
created: '2026-08-17'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
evidence_scope:
- tests/unit/verify/test_watermark.py
- tests/unit/verify/test_backpressure.py
- tests/unit/verify/test_verify_runner.py
- tests/unit/test_land_cmd_backpressure.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/verify/test_watermark.py::TestCommitsSinceWatermark::test_counts_raw_git_commits_not_queue_entries
- tests/unit/verify/test_watermark.py::TestCommitsSinceWatermark::test_zero_at_the_watermark_itself
- tests/unit/verify/test_watermark.py::TestCommitsSinceWatermark::test_none_when_watermark_commit_unresolvable
- tests/unit/verify/test_backpressure.py::TestRapidSoftWarning::test_no_watermark_yet_is_none
- tests/unit/verify/test_backpressure.py::TestRapidSoftWarning::test_below_threshold_is_none
- tests/unit/verify/test_backpressure.py::TestRapidSoftWarning::test_stale_watermark_trips_the_soft_warning
- tests/unit/verify/test_backpressure.py::TestRapidSoftWarning::test_toml_override
- tests/unit/verify/test_verify_runner.py::TestBuildStatus::test_commits_since_watermark_reflects_real_git_gap_not_queue_depth
- tests/unit/test_land_cmd_backpressure.py::TestApplyBackpressure::test_rapid_profile_calls_soft_warning_never_blocks
designated_repro_test: tests/unit/verify/test_watermark.py::TestCommitsSinceWatermark::test_counts_raw_git_commits_not_queue_entries
acceptance:
- text: given a watermark stale by hundreds of commits, when the operator runs frob
    verify status, then the reported depth matches the real commits-since-watermark
    or is named for what it measures
  evidence:
  - tests/unit/verify/test_watermark.py::TestCommitsSinceWatermark::test_counts_raw_git_commits_not_queue_entries
  - tests/unit/verify/test_watermark.py::TestCommitsSinceWatermark::test_zero_at_the_watermark_itself
  - tests/unit/verify/test_watermark.py::TestCommitsSinceWatermark::test_none_when_watermark_commit_unresolvable
  - tests/unit/verify/test_backpressure.py::TestRapidSoftWarning::test_no_watermark_yet_is_none
  - tests/unit/verify/test_backpressure.py::TestRapidSoftWarning::test_below_threshold_is_none
  - tests/unit/verify/test_backpressure.py::TestRapidSoftWarning::test_stale_watermark_trips_the_soft_warning
  - tests/unit/verify/test_backpressure.py::TestRapidSoftWarning::test_toml_override
  - tests/unit/verify/test_verify_runner.py::TestBuildStatus::test_commits_since_watermark_reflects_real_git_gap_not_queue_depth
  - tests/unit/test_land_cmd_backpressure.py::TestApplyBackpressure::test_rapid_profile_calls_soft_warning_never_blocks
- text: given the rapid profile, when verification debt crosses a depth/age threshold,
    then the operator is warned at a surface they already read, without blocking any
    land
  evidence:
  - tests/unit/verify/test_watermark.py::TestCommitsSinceWatermark::test_counts_raw_git_commits_not_queue_entries
  - tests/unit/verify/test_watermark.py::TestCommitsSinceWatermark::test_zero_at_the_watermark_itself
  - tests/unit/verify/test_watermark.py::TestCommitsSinceWatermark::test_none_when_watermark_commit_unresolvable
  - tests/unit/verify/test_backpressure.py::TestRapidSoftWarning::test_no_watermark_yet_is_none
  - tests/unit/verify/test_backpressure.py::TestRapidSoftWarning::test_below_threshold_is_none
  - tests/unit/verify/test_backpressure.py::TestRapidSoftWarning::test_stale_watermark_trips_the_soft_warning
  - tests/unit/verify/test_backpressure.py::TestRapidSoftWarning::test_toml_override
  - tests/unit/verify/test_verify_runner.py::TestBuildStatus::test_commits_since_watermark_reflects_real_git_gap_not_queue_depth
  - tests/unit/test_land_cmd_backpressure.py::TestApplyBackpressure::test_rapid_profile_calls_soft_warning_never_blocks
- text: given a drain mechanism exists, when it runs, then the watermark advances
    and a subsequent sweep baselines against the fresh watermark rather than a 6-day-old
    one
  evidence:
  - tests/unit/verify/test_watermark.py::TestCommitsSinceWatermark::test_counts_raw_git_commits_not_queue_entries
  - tests/unit/verify/test_watermark.py::TestCommitsSinceWatermark::test_zero_at_the_watermark_itself
  - tests/unit/verify/test_watermark.py::TestCommitsSinceWatermark::test_none_when_watermark_commit_unresolvable
  - tests/unit/verify/test_backpressure.py::TestRapidSoftWarning::test_no_watermark_yet_is_none
  - tests/unit/verify/test_backpressure.py::TestRapidSoftWarning::test_below_threshold_is_none
  - tests/unit/verify/test_backpressure.py::TestRapidSoftWarning::test_stale_watermark_trips_the_soft_warning
  - tests/unit/verify/test_backpressure.py::TestRapidSoftWarning::test_toml_override
  - tests/unit/verify/test_verify_runner.py::TestBuildStatus::test_commits_since_watermark_reflects_real_git_gap_not_queue_depth
  - tests/unit/test_land_cmd_backpressure.py::TestApplyBackpressure::test_rapid_profile_calls_soft_warning_never_blocks
threat: null
component: verify
anchor: false
anchor_reason: null
land_commit: 13e3026ad550af31f8f1ae45a2db98591c99c7ea
---
MEASURED 2026-08-17. `frob verify status` reports:

  watermark:         f0ab85d0 (2026-08-11 03:39, SIX DAYS old)
  watermark age:     554769s
  unverified depth:  84
  oldest unverified: T-2157's land, 554252s old
  quarantine:        clear (raised 06:28 today, auto-cleared 06:29 as T-2266)

`git rev-list --count f0ab85d0..main` is **403**, not 84 -- so the depth
figure an operator reads understates the real backlog by ~5x. Whatever
`unverified depth` counts, it is not commits-since-watermark, and the
gap is not documented at the surface where the number is printed.

THE STRUCTURAL POINT: `frob.toml` sets `[profile] profile = "rapid"`, and
`frob.verify._backpressure.ceilings_for_profile` returns
`BackpressureCeilings(max_depth=None, max_age_s=None)` for RAPID --
"unbounded on both axes (never blocks, by construction)" per its own
docstring. So under `rapid` there is NOTHING that forces the deferred
verification to ever run. Deferred becomes never. The watermark has not
advanced in 6 days and 403 commits while sweeps ran daily, filed tickets,
and cleared quarantine.

WHY THIS COMPOUNDS: the rapid sweep re-derives findings against a rolling
baseline anchored at a 6-day-old watermark. That is the direct mechanism
behind the recurring "post-land sweep regression: N new identities" tickets
whose findings turn out to be mostly pre-existing (T-2260's shape, and the
already-recorded lesson that 5 of 6 "new" identities in a sweep-filed
ticket were pre-existing). A stale baseline manufactures false attribution,
which costs a triage ticket each time.

This is not an argument for switching to `standard` -- rapid's whole point
is keeping the multi-minute check off the land critical path, and that is
working (measured land wall time 93-148s, no land timeouts in 15
invocations). The gap is that rapid has an unbounded DEFER with no DRAIN.

FIX DIRECTION (design decision needed, do not guess):
 (a) a drain step -- something that actually advances the watermark on a
     cadence (idle-time sweep, explicit `frob verify drain`, or a
     coordinator-invoked catch-up), independent of land; and/or
 (b) a soft ceiling for rapid: never BLOCK a land (preserve the
     never-blocks contract), but WARN loudly at the surfaces an operator
     already reads once depth/age crosses a threshold -- per the standing
     "automatic over commands" directive, a drain that requires knowing a
     command will not get run.
 (c) reconcile `unverified depth` with the real commit count, or rename it
     to say what it actually measures.

ACCEPTANCE NOTE: any fix must be verified against a REAL stale watermark,
not a synthetic one-commit gap -- the failure only shows up at depth.