---
id: T-0602
title: 'serve: per-obligation dependency-tracked partial re-evaluation inside gate
  dispatch'
state: done
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0177
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- src/frob/serve/**
- tests/test_gate_cache.py
- docs/modules/serve.md
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_gate_cache.py
  reason: 'Implementation needs a dedicated test module (tests/test_gate_cache.py)
    for

    the cold-diff oracle property test plus unit tests, and docs/modules/serve.md

    + docs/modules/gates.md updates to describe the new per-gate cache and

    close the doc-drift gap serve.md''s own "What it does NOT cover" section

    named. Neither original glob (src/frob/gates/**, src/frob/serve/**) covers

    tests/** or docs/modules/**, so adding them explicitly via scope amendment

    rather than touching untracked files.

    '
  actor: logan
  at: '2026-07-27'
- op: add
  glob: docs/modules/serve.md
  reason: 'Implementation needs a dedicated test module (tests/test_gate_cache.py)
    for

    the cold-diff oracle property test plus unit tests, and docs/modules/serve.md

    + docs/modules/gates.md updates to describe the new per-gate cache and

    close the doc-drift gap serve.md''s own "What it does NOT cover" section

    named. Neither original glob (src/frob/gates/**, src/frob/serve/**) covers

    tests/** or docs/modules/**, so adding them explicitly via scope amendment

    rather than touching untracked files.

    '
  actor: logan
  at: '2026-07-27'
- op: add
  glob: docs/modules/gates.md
  reason: 'Implementation needs a dedicated test module (tests/test_gate_cache.py)
    for

    the cold-diff oracle property test plus unit tests, and docs/modules/serve.md

    + docs/modules/gates.md updates to describe the new per-gate cache and

    close the doc-drift gap serve.md''s own "What it does NOT cover" section

    named. Neither original glob (src/frob/gates/**, src/frob/serve/**) covers

    tests/** or docs/modules/**, so adding them explicitly via scope amendment

    rather than touching untracked files.

    '
  actor: logan
  at: '2026-07-27'
evidence:
- tests/test_gate_cache.py::TestTrackedSnapshot::test_symbol_iteration_records_file
- tests/test_gate_cache.py::TestTrackedSnapshot::test_getitem_records_only_accessed_key
- tests/test_gate_cache.py::TestEvaluateCacheableGate::test_miss_then_hit_skips_second_call
- tests/test_gate_cache.py::TestEvaluateCacheableGate::test_edit_to_untouched_file_stays_a_hit
- tests/test_gate_cache.py::TestEvaluateCacheableGate::test_edit_to_touched_file_forces_miss
- tests/test_gate_cache.py::TestEvaluateCacheableGate::test_new_untouched_file_forces_miss_membership_guard
- tests/test_gate_cache.py::TestEvaluateCacheableGate::test_extra_change_forces_miss
- tests/test_gate_cache.py::TestEvaluateCacheableGate::test_invalidate_forces_next_call_to_miss
- tests/test_gate_cache.py::TestRunGatesUseCache::test_use_cache_false_is_default_and_unaffected
- tests/test_gate_cache.py::TestRunGatesUseCache::test_use_cache_true_produces_identical_report_to_cold
- tests/test_gate_cache.py::TestColdDiffOracle::test_cache_agrees_with_cold_across_random_edits
designated_repro_test: null
acceptance:
- text: GIVEN a warm daemon and a one-file edit WHEN frob_check_delta runs THEN only
    obligations whose inputs include that file are re-evaluated AND verify mode shows
    zero fingerprint mismatch vs a cold run
  evidence:
  - tests/test_gate_cache.py::TestEvaluateCacheableGate::test_edit_to_untouched_file_stays_a_hit
  - tests/test_gate_cache.py::TestColdDiffOracle::test_cache_agrees_with_cold_across_random_edits
  - tests/test_gate_cache.py::TestRunGatesUseCache::test_use_cache_true_produces_identical_report_to_cold
threat: null
component: null
---
Deferred remainder of T-0177 deliverable 2. The warm daemon caches graph snapshot, baseline, and collected test ids, and frob_check_delta filters full-run results against the stamped baseline -- but run_gates itself still evaluates EVERY gate in full on each call. Build per-obligation input tracking inside gate dispatch so a delta call evaluates only obligations whose inputs changed, with the verify=True cold-diff mode as the correctness oracle (incremental results must provably match a cold frob check). NOTE: T-0177's Done report references this as T-0602 (ex-draft, id lost at land); the draft block did not survive  (same draft-loss failure as T-0401's draft -- T-0577 tracks the land-time fix), so this ticket is its real replacement.