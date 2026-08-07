---
id: T-1353
title: Investigate xdist coverage-merge symbol-level data drop (T-1335 residue)
state: done
kind: bug
origin: human
created: '2026-07-31'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_coverage.py
- Makefile
- tests/unit/test_makefile_coverage.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_makefile_coverage.py
  reason: 'T-1353''s fix requires proving both root causes (worker OOM crashes,

    serial-rerun timeout-method corruption) against the real Makefile recipe

    text without a duplicated/drifting reimplementation, and there is no

    Makefile-native "symbol" `frob:tests` can bind evidence to -- adding a

    regression test to the same file T-1335 already established for exactly

    this purpose (TestCombineRecoversDisjointSessions) is the only way to

    bind real pytest evidence to this ticket''s Makefile-only scope.

    '
  actor: logan
  at: '2026-07-31'
evidence:
- tests/unit/test_makefile_coverage.py::TestCombineRecoversDisjointSessions::test_two_disjoint_sessions_combine_to_full_coverage
- tests/unit/test_makefile_coverage.py::TestStampFailurePropagation::test_stamp_failure_after_green_suite_fails_the_recipe
- tests/unit/test_makefile_coverage.py::TestStampFailurePropagation::test_green_suite_and_green_stamp_still_exits_zero
- tests/unit/test_makefile_coverage.py::TestCoverageXmlIgnoreErrors::test_coverage_xml_invocations_pass_ignore_errors
designated_repro_test: null
threat: null
component: null
---
Filed while working T-1335 (Makefile-only scope). T-1335's own recipe fix
now detects a crashed xdist worker ("node down: Not properly terminated")
during `make coverage` and escalates to a full serial rerun to recover
that worker's entirely-lost coverage data -- confirmed live during T-1335's
own verification (5+ workers crashed per run, 3 separate runs, consistent
with this session's known WSL-OOM resource contention).

However, several agents independently reported deflated/zeroed TEST005
numbers for symbols that are genuinely well-tested, in a pattern (def line
hits=1, every body line hits=0) that looks like a PARTIAL merge -- one
worker's data for a line survived, another worker's data for the rest did
not -- rather than simple staleness. The worker-crash fix in T-1335 may
already explain some/most of this (a crashed worker's data vanishing
outright), but it does not obviously explain a partial per-symbol split
this precise, and should be checked against `coverage combine`'s own
merge behavior in src/frob/gates/_coverage.py (module_join_fraction,
stale_by_mtime) and/or `coverage combine` itself, independent of whether
any worker actually crashed on a given run.

Concrete repro cases collected across multiple agents (validate a fix,
or T-1335's own fix, against these -- expect all four at their real, high
values once combine/merge is trustworthy):
  src/frob/strata check_process_bounds_obligations: stamp 6.7%, real ~98%
  src/frob/strata check_self_conformance: stamp 0.0%, real ~95%
  src/frob/release authoritative_version: def hits=1, every body line hits=0
  src/frob/app worktree_runner.py::run: false 0.0%, attributed to xdist
    coverage-merge dropping the symbol's branch data

Not T-1333 (coverage.py + CSafeLoader corrupts a YAML parse under --cov)
-- checked, that is a distinct failure mode (an actual test failure under
instrumentation via a C-extension/tracer interaction), not a coverage-data
merge/drop issue. Leave T-1333 alone; do not fold it in here.

Suggest: reproduce with a small multi-worker fixture that deliberately
returns partial per-worker data and confirm whether `coverage combine`
(stdlib) or this repo's own load_coverage/module aggregation
(src/frob/gates/_coverage.py) is where data is actually lost; if it's a
site-wide coverage.py behavior, consider whether combine ordering/dedup
in the Makefile also plays a role (T-1335's own verification run combined
176 files but skipped 280 -- worth understanding whether 280 "skipped"
files were legitimate duplicates/empties or lost data).