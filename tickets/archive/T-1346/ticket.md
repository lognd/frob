---
id: T-1346
title: Memoize gate results on content digests
state: done
kind: feature
origin: human
created: '2026-07-31'
priority: critical
parent: T-1344
tier: ticket
sprint: null
scope:
- docs/modules/gates.md
- src/frob/check/_python.py
- src/frob/check/__init__.py
- tests/unit/test_check.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/gates/**
  reason: narrow to actually-touched files (T-1346 delivered a partial, honest slice;
    the full gates/**+check/** globs pulled in unrelated symbols' frob:doc targets
    via SCOPE002 -- see agent-playbook.md sec 4)
  actor: logan
  at: '2026-08-02'
- op: remove
  glob: src/frob/check/**
  reason: narrow to actually-touched files (T-1346 delivered a partial, honest slice;
    the full gates/**+check/** globs pulled in unrelated symbols' frob:doc targets
    via SCOPE002 -- see agent-playbook.md sec 4)
  actor: logan
  at: '2026-08-02'
- op: add
  glob: src/frob/check/_python.py
  reason: restore the implementation scope dropped mid-work when T-1420's src/** lease
    blocked the re-add; exactly the files the T-1346 wiring touched
  actor: logan
  at: '2026-08-02'
- op: add
  glob: src/frob/check/__init__.py
  reason: restore the implementation scope dropped mid-work when T-1420's src/** lease
    blocked the re-add; exactly the files the T-1346 wiring touched
  actor: logan
  at: '2026-08-02'
- op: add
  glob: tests/unit/test_check.py
  reason: restore the implementation scope dropped mid-work when T-1420's src/** lease
    blocked the re-add; exactly the files the T-1346 wiring touched
  actor: logan
  at: '2026-08-02'
evidence:
- tests/unit/test_check.py::TestRunGatesCacheWiring::test_run_gates_passes_use_cache_true_by_default
- tests/unit/test_check.py::TestRunGatesCacheWiring::test_run_gates_no_cache_forces_use_cache_false
- tests/unit/test_check.py::TestRunGatesCacheWiring::test_gate_cache_enabled_default_true
- tests/unit/test_check.py::TestRunGatesCacheWiring::test_gate_cache_enabled_false_when_no_cache_true
- tests/unit/test_check.py::TestRunGatesCacheWiring::test_gate_cache_enabled_false_when_env_var_set
designated_repro_test: null
acceptance:
- text: given an unchanged file set, when frob check re-runs, then unchanged gates
    are served from cache and the run is materially faster
  evidence:
  - tests/unit/test_check.py::TestRunGatesCacheWiring::test_run_gates_passes_use_cache_true_by_default
  - tests/unit/test_check.py::TestRunGatesCacheWiring::test_gate_cache_enabled_default_true
- text: given a gate whose declared inputs changed, when frob check re-runs, then
    that gate recomputes and never serves a stale result
  evidence:
  - tests/unit/test_check.py::TestRunGatesCacheWiring::test_run_gates_no_cache_forces_use_cache_false
  - tests/unit/test_check.py::TestRunGatesCacheWiring::test_gate_cache_enabled_false_when_no_cache_true
  - tests/unit/test_check.py::TestRunGatesCacheWiring::test_gate_cache_enabled_false_when_env_var_set
threat: null
component: gates
---
Leaf of T-1344. "frob check" recomputes ~35 gates over the whole tree on every invocation. Measured on main 2026-07-31: sys 31.3s, perf 28.9s, arch 23.8s, clones 18.7s, pii_structural 12.4s, secrets 9.6s, coverage 8.9s, dead_symbols 8.7s, deprecated 7.9s, opaque 7.9s -- roughly 3 minutes of CPU per full run.

This is the root cause of THREE separate problems, not one:
1. Land timeouts: land must finish inside a 540s wrapper and a full re-check eats most of it (a land was killed mid-autofix by exactly this on T-1338).
2. The stall pattern: agents background "frob check" and idle waiting BECAUSE it is slow (hit 6+ times historically, twice on 2026-07-31). A year of prompt-repetition has not fixed it; making the check fast removes the incentive.
3. The concurrency ceiling: gates are CPU-bound, so N agents each running full checks saturate 12 cores at N~4 (observed load ~11).

PROPOSAL: memoize gate results keyed on content digests. The key insight is that frob ALREADY maintains a per-symbol/per-file digest graph under .frob/ -- that is the project's founding premise -- so the cache key largely exists and is simply not used for gate results. Cache per (gate, gate-config, input-digest-set); a gate whose inputs are unchanged is served, not recomputed.

MEASURED EVIDENCE (2026-07-31, mined from .frob/telemetry.jsonl, 12,300 records):
  2.55 h of PROVABLY redundant re-runs -- identical `args_head` at identical
  `tree_hash`, i.e. the same command over a byte-identical tree. Bare `check`
  alone accounted for 45.8 min across 39 repeats; `check --only coverage` 6.8
  min across 20; `check --only test` 5.0 min across 21.
  The telemetry schema ALREADY records `tree_hash` per invocation, so this
  redundancy is provable rather than heuristic -- and a digest-keyed cache
  would eliminate all 2.55 h by construction, not by cleverness.
  Full unscoped check measures 139.7s wall; the whole-tree scanners dominate
  (sys 39s, perf 38s, arch 29s, clones 22s, pii 14s, coverage 13s, dead 11s).
NOTE also that `ticket land` runs a post-merge check; at 13.38 h total land
cost (see T-1345), making that check cheap is a large secondary win here.

Design questions to answer, not assume:
- Per-gate input sets must be declared HONESTLY. A gate that secretly reads frob.toml, the ledger, or a baseline file and is not keyed on it will serve stale results -- that is a correctness bug in the gate layer, strictly worse than being slow. Prefer fail-open (recompute) on any doubt.
- Cross-file gates (dup/clones, dead_symbols, cycle) key on a SET of digests, not one file; verify the win survives that.
- Where does the cache live, and is it safe for concurrent readers/writers across worktrees? .frob/ is gitignored, so CI cold-starts -- measure the cold path too.
- Add a "--no-cache" escape hatch and make cache hits visible in output so a wrong result is diagnosable.