---
id: T-0711
title: 'hot-graph sketch store: log-bucket quantile sketches with decayed merge in
  .frob sqlite'
state: done
kind: feature
origin: human
created: '2026-07-22'
priority: medium
parent: T-0709
tier: ticket
sprint: null
scope:
- src/frob/stats/**
- src/frob/perf/**
- tests/unit/perf/
- docs/modules/perf.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/perf.md
  reason: 'T-0711''s plan requires docs/modules/perf.md updated in the same change
    (agent playbook + engineering-principles DOCUMENT AS YOU GO); scope initially
    only listed source/test globs

    '
  actor: logan
  at: '2026-07-23'
evidence:
- tests/unit/perf/test_sketch_store.py::TestQuantileSketchAlgebra::test_bimodal_quantiles_within_relative_error_and_under_1kb
- tests/unit/perf/test_sketch_store.py::TestQuantileSketchAlgebra::test_merge_is_associative
- tests/unit/perf/test_sketch_store.py::TestSketchStore::test_decayed_merge_converges_toward_recent_run_distribution
- tests/unit/perf/test_sketch_store.py::TestSketchStore::test_store_cap_evicts_coldest_section_first
designated_repro_test: null
acceptance:
- text: GIVEN bimodal latencies (1ms and 100ms modes) WHEN sketched at alpha=2 percent
    THEN p10/p50/p90 read back within relative error and the serialized sketch is
    <1KB; GIVEN repeated runs THEN decayed merge converges and the store stays under
    its cap
  evidence:
  - tests/unit/perf/test_sketch_store.py::TestQuantileSketchAlgebra::test_bimodal_quantiles_within_relative_error_and_under_1kb
  - tests/unit/perf/test_sketch_store.py::TestQuantileSketchAlgebra::test_merge_is_associative
  - tests/unit/perf/test_sketch_store.py::TestSketchStore::test_decayed_merge_converges_toward_recent_run_distribution
  - tests/unit/perf/test_sketch_store.py::TestSketchStore::test_store_cap_evicts_coldest_section_first
threat: null
component: null
---
Child 2: the user-specified compact encoding. DDSketch-style log-scale bucket sketch per section/edge: tunable relative-error alpha (frob.toml, default ~2 percent), mergeable, serialized to .frob sqlite keyed by stable section id (symbol digest + section kind + span -- survives line drift via the existing symbol digest machinery). prior->update = merge(current_run_sketch, decay(stored_prior, half_life_runs)); deciles/any-quantile computed at read time, never stored. Size budget enforced: a repo-wide store cap (~100KB default) with eviction of coldest sections, so it structurally cannot grow to megabytes. Property tests: merge associativity, quantile relative-error bound holds under adversarial bimodal inputs (the anti-normal-distribution case).