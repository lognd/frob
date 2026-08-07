---
id: T-0710
title: 'hot-graph collector: sampling profiler + normalized-model section attribution'
state: done
kind: feature
origin: human
created: '2026-07-22'
priority: medium
parent: T-0709
tier: ticket
sprint: null
scope:
- src/frob/perf/**
- src/frob/arch/**
- tests/unit/perf/
- docs/modules/perf.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/perf.md
  reason: T-0710's public API additions (hot-graph collector contract/resolver/sampler)
    need doc coverage; docs/modules/perf.md is the existing home for this module's
    public API docs
  actor: logan
  at: '2026-07-22'
evidence:
- tests/unit/perf/test_hotgraph.py::TestResolveStream::test_leaf_in_loop_body_attributes_to_loop_section
- tests/unit/perf/test_hotgraph.py::TestResolveStream::test_leaf_in_branch_body_attributes_to_branch_section
- tests/unit/perf/test_hotgraph.py::TestResolveStream::test_call_edge_classified_external_when_callee_unmodeled
- tests/unit/perf/test_hotgraph.py::TestResolveStream::test_call_edge_classified_internal_when_callee_modeled
- tests/unit/perf/test_hotgraph.py::TestResolveStream::test_unresolvable_leaf_is_unattributed_never_dropped
- tests/unit/perf/test_hotgraph.py::TestResolveStream::test_empty_stack_produces_no_hits
- tests/unit/perf/test_hotgraph.py::TestStackSampler::test_collects_at_least_one_sample_over_a_hot_loop
- tests/unit/perf/test_hotgraph.py::TestStackSampler::test_stop_without_start_is_safe_and_empty
- tests/unit/perf/test_hotgraph.py::TestStackSampler::test_start_is_idempotent
- tests/unit/perf/test_hotgraph.py::TestStackSampler::test_max_depth_caps_frame_count
- tests/unit/perf/test_harness_sampling.py::TestHarnessSampling::test_unsampled_run_is_unaffected
- tests/unit/perf/test_harness_sampling.py::TestHarnessSampling::test_sampled_run_logs_hotgraph_summary
- tests/unit/perf/test_harness_sampling.py::TestHarnessSampling::test_sampled_run_resolves_the_hot_loop_section
- tests/unit/perf/test_hotgraph.py::TestResolveStream::test_loop_body_after_nested_branch_never_attributes_to_branch
- tests/unit/perf/test_hotgraph.py::TestStackSampler::test_overhead_under_five_percent
designated_repro_test: null
acceptance:
- text: GIVEN a fixture with a hot inner loop calling an external function WHEN the
    collector runs THEN samples attribute to the loop section and the call edge with
    <5 percent measured overhead
  evidence:
  - tests/unit/perf/test_hotgraph.py::TestResolveStream::test_loop_body_after_nested_branch_never_attributes_to_branch
  - tests/unit/perf/test_hotgraph.py::TestStackSampler::test_overhead_under_five_percent
threat: null
component: null
---
Child 1: a sampling collector (py-spy-style stack sampling or sys.monitoring on 3.12+, config-tunable rate) running during the perf harness and optionally frob test; each sample's frame lines map to enclosing sections via the normalized model's line spans (loop bodies, branch arms, function bodies) and call edges (external vs internal callee classification from the import graph). Output: per-section and per-edge hit streams handed to the sketch store. Overhead budget: <5 percent at default rate, measured and documented. CONTRACT MANDATE (user, 2026-07-22): the hit-stream format this ticket defines is LANGUAGE-NEUTRAL -- (file, line, weight) frames resolved to section ids via the normalized model, with nothing Python-specific in the stream or the store; the Python sampler is merely the first producer. Sibling ticket ingests native/V8/JVM profiles into the same stream (per-language collector adapters, mirroring the LanguageAdapter pattern).