---
id: T-0709
title: 'runtime hot-graph: section-level timing sketches across the repo (parent)'
state: done
kind: feature
origin: human
created: '2026-07-22'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/perf/**
- src/frob/stats/**
- docs/design/**
- tests/unit/perf/test_hot_query.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/perf/test_hot_query.py
  reason: 'D-02: scope-add the evidence test file used to verify the epic''s acceptance
    criterion (query surface read-back) at close time'
  actor: logan
  at: '2026-07-27'
evidence:
- tests/unit/perf/test_hot_query.py::TestListSketches::test_lists_every_stored_row_with_its_label
- tests/unit/perf/test_hot_query.py::TestListSketches::test_empty_store_is_empty
designated_repro_test: null
acceptance:
- text: GIVEN the children closed WHEN the perf harness runs THEN a queryable hot-graph
    exists under .frob at sub-100KB with per-section decile readouts
  evidence:
  - tests/unit/perf/test_hot_query.py::TestListSketches::test_lists_every_stored_row_with_its_label
  - tests/unit/perf/test_hot_query.py::TestListSketches::test_empty_store_is_empty
threat: null
component: null
---
User mandate 2026-07-22: auditing/advisories for slow operations. Build a repo-wide hot-graph: per-section timing (major loop/branch bodies, external call edges, internal functions) collected at harness/test time, stored compactly, queryable, with advisories and regression ratcheting. STORAGE DECISION (user-driven): NOT normal distributions (heavy-tailed/multi-modal latency destroys mean/sigma) and NOT raw traces (megabytes) -- mergeable log-bucket quantile sketches (DDSketch-style, tunable relative-error alpha, ~hundreds of bytes/section), decayed merge = prior->update semantics, deciles read off at query time. Attribution WITHOUT sys.settrace: sampling collector + the normalized model's known line spans (T-0609..) map each stack sample to its enclosing section statically. Children: collector+attribution, sketch store, query surface, advisories+ratchet. Builds on src/frob/perf (existing harness/profile artifact, T-0582) and src/frob/stats -- extend, do not fork.