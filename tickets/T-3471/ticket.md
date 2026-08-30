---
id: T-3471
title: 'test_probe_catches_the_in_root_write_positive_control races on CI: the sampler
  never observes the dirty root'
state: queued
kind: bug
origin: agent
created: '2026-08-30'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/test_land_record_commit.py
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
MEASURED on GitHub Actions run 33298117154 (ubuntu-latest, HEAD f821615ca, 2026-08-30), the first run where ubuntu completes the suite (17.7 min, 8 failures of 12777). Reproduce locally by node id with -p no:xdist first; a test that passes locally but fails on CI has an environment dependency and must be made hermetic, never skipped.

FAILING: tests/unit/test_land_record_commit.py::TestRecordLandCommitOutOfTree::test_probe_catches_the_in_root_write_positive_control
    AssertionError: the probe saw a CLEAN root across an in-root write+add+commit -- it cannot detect the state the AFTER arm claims is gone
T-3442 measured this test as passing locally every time (6 runs) and failing only on CI, and made no change. It still fails on CI. The probe samples `git status` during an in-root write+add+commit; on the runner the commit completes before the sampler observes the dirty state. Make the positive control deterministic: hold the dirty state open (e.g. write + add, sample, THEN commit; or block the commit behind an event the sampler releases) so the probe is proven able to see a dirty root without a race. Keep the must-stay-quiet arm unchanged.
