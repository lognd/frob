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
- op: remove
  glob: uv.lock
  reason: uv.lock is land-owned (T-0731) -- regenerated at land time, not a ticket-scoped
    file
  actor: logan
  at: '2026-09-02'
body_changes:
- mode: append
  reason: waive BUG002 -- CI-load-dependent flake is not a deterministic parent-commit
    repro case
  actor: logan
  at: '2026-09-02'
  old_length: 582
  new_length: 1103
evidence:
- tests/unit/perf/test_hotgraph.py::TestStackSampler::test_overhead_under_five_percent
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
CI flaky whack-a-mole: tests/unit/perf/test_hotgraph.py::TestStackSampler::test_overhead_under_five_percent flaked in run 33698082419 (ubuntu). T-3655 already widened tolerance once; CPU-relative perf ratio is fundamentally noisy under xdist on shared CI runners, serial xdist_group doesn't fully fix it (T-0760/T-3655). Add pytest-rerunfailures and apply bounded @pytest.mark.flaky(reruns=2, reruns_delay=1) ONLY to genuinely load-sensitive tests (CPU-relative perf ratios) in tests/unit/perf/, with reason comments. Do not touch cache/graph_build_lock tests (owned by sibling AU).

frob:waive BUG002 reason="the defect is CI-runner-load-dependent nondeterministic flakiness, not a deterministic code bug the suite can reproduce/fix at a single commit -- the test passes at both parent and fix commit locally by design (it only ever fails under real CI CPU contention), so BUG002's fail-then-pass repro shape does not apply; the fix is a test-infrastructure mitigation (bounded rerun), verified instead by the marked test still passing normally and by CI (the true environment where the flake occurs)"