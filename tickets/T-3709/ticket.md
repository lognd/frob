---
id: T-3709
title: Bounded rerun for load-sensitive CPU-relative perf tests
state: in-progress
kind: bug
origin: human
created: '2026-09-02'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/perf/**
- pyproject.toml
- uv.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: tests/conftest.py
  reason: T-3707 holds conftest.py lease; register pytest markers via pyproject.toml
    ini_options instead
  actor: logan
  at: '2026-09-02'
- op: remove
  glob: .github/workflows/ci.yml
  reason: T-3707 holds ci.yml lease; rerunfailures markers work with no CLI flag needed,
    so ci.yml is not required
  actor: logan
  at: '2026-09-02'
- op: add
  glob: uv.lock
  reason: uv sync regenerates uv.lock as a direct consequence of adding pytest-rerunfailures
    to pyproject.toml
  actor: logan
  at: '2026-09-02'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
CI flaky whack-a-mole: tests/unit/perf/test_hotgraph.py::TestStackSampler::test_overhead_under_five_percent flaked in run 33698082419 (ubuntu). T-3655 already widened tolerance once; CPU-relative perf ratio is fundamentally noisy under xdist on shared CI runners, serial xdist_group doesn't fully fix it (T-0760/T-3655). Add pytest-rerunfailures and apply bounded @pytest.mark.flaky(reruns=2, reruns_delay=1) ONLY to genuinely load-sensitive tests (CPU-relative perf ratios) in tests/unit/perf/, with reason comments. Do not touch cache/graph_build_lock tests (owned by sibling AU).