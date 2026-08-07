## Done report

Duplicate of T-0760, resolved there. Read both ticket bodies before
implementing: T-0759 (scope tests/unit/perf/test_hotgraph.py) and T-0760
(scope tests/unit/perf/, src/frob/perf/**) both report the exact same
fragility in the exact same test --
TestStackSampler.test_overhead_under_five_percent's wall-clock overhead
measurement being inflated by pytest-xdist cross-worker core contention,
found during T-0710 review round 2 (T-0759) and named directly against
T-0710 (T-0760). T-0759's scope is a strict subset of T-0760's.

No separate diff was made under T-0759 to avoid re-doing the same fix
twice or producing two divergent implementations of the same test. The
actual fix (switch the test to time.process_time() CPU-time measurement,
plus a worker_id-gated tolerance: 5 percent when uncontended, a
documented 35 percent when running under an xdist worker) was implemented
and verified under T-0760's Done report; see that report for the full
verification transcript (12 passed x2 under -n0, 12 passed x5 under the
repo's default -n auto including one run under measured host load average
33 on a 12-core box, ruff clean, all five frob check --only stage groups
0 errors, no out-of-scope deletions).

Recommend the coordinator drop T-0759 as superseded by T-0760, or close
both citing the same evidence -- coordinator's call per the dispatch
instructions.

Cuts: none (no distinct work existed to cut; this was genuinely the same
ticket filed twice under different titles).

Filed: none.

### Changed
(no changed files detected)

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
