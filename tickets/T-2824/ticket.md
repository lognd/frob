---
id: T-2824
title: 'LARGE001: split or waive oversized misc small-package modules + native (rust)
  files'
state: done
kind: bug
origin: agent
created: '2026-08-21'
priority: medium
parent: T-2375
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/check/__init__.py
- src/frob/check/_python.py
- src/frob/lang/__init__.py
- src/frob/lang/_support.py
- src/frob/perf/_effect_summaries.py
- src/frob/perf/_rules.py
- src/frob/doctor.py
- src/frob/dup/_pipeline/_fingerprint.py
- src/frob/serve/_socketd.py
- src/frob/testing/_coverage_refresh.py
- src/frob/verify/_worker.py
- scripts/fleet_status.py
- src/frob/_cli_parsers/_misc.py
- frob-core/src/capability_python.rs
- frob-core/src/lib.rs
- strata-core/src/lib.rs
- strata-core/src/parse/mod.rs
evidence_scope:
- tests/test_arch_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: record BUG002 waiver rationale and the direct re-measurement method used,
    same shape as prior series tickets
  actor: logan
  at: '2026-08-21'
  old_length: 1545
  new_length: 2548
evidence:
- tests/test_arch_gate.py::TestArchGateLargeFile::test_large_file_fires_large001_warn
designated_repro_test: null
acceptance:
- text: 'given the batch''s 17 files, when arch_gate + _apply_waivers is run directly
    against a build_graph snapshot, then none of the 17 files appear in the unwaived
    LARGE001 kept-set (verified: 0 of 17, remaining 30 unwaived repo-wide are all
    in src/frob/gates/** or src/frob/strata/**, out of scope)'
  evidence:
  - tests/test_arch_gate.py::TestArchGateLargeFile::test_large_file_fires_large001_warn
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Child of T-2375 (LARGE001 burn-down epic). Measured 2026-08-21 via 'frob check --json --budget 500' (severity=warning, code=LARGE001) -- do NOT trust this ticket's own file list without re-measuring first; the tree moves. Each file listed here exceeds frob.toml's max_file_lines=800 threshold.

Per-file disposition is a JUDGMENT CALL, not a mechanical split: T-1651 already established that several LARGE001 files in this repo (_models.py, _waive.py, _land_git_ops.py, check_runner.py, config.py, sys_runner.py -- NOT in this batch, already resolved via frob:waive) are cohesive single-concern files where a line-count split would cut a real seam apart and be STRICTLY WORSE than the warning. For each file in this batch: either (a) find a genuine consumer-set/responsibility seam and split it, or (b) if no real seam exists, add a 'frob:waive LARGE001 reason="..."' with the same rigor T-1651's own waivers show (naming why no split is a real seam, not just 'it is big'). Both are valid closure for a given file; a forced split with no real boundary is not.

Do NOT touch src/frob/strata/_selfconform.py -- it is T-2729's own ticket (largest LARGE001 offender, 2290 lines), already filed, do not absorb it here.

Closure for this CHILD ticket: every file below reads as severity=note (waived) or disappears from LARGE001 entirely when re-measured. Do NOT flip LARGE001 warning->error severity here -- that promotion is T-2375's own final step, deferred until every sibling batch lands (promoting early reds main for siblings' still-open debt).

<!-- frob:waive BUG002 reason="this ticket's disposition is split-or-waive judgment calls across 17 files (13 Python, 4 Rust) -- no functional code changed and no single reproducible defect exists to bind a failing-at-parent test to; the correct closure per T-2375's own body is a frob:waive LARGE001 directive on each file with T-1651-grade reasoning, not a forced split. Two files (scripts/fleet_status.py, frob-core/src/lib.rs) DO have a genuine investigated seam, filed as follow-up tickets rather than split here because new files are outside this ticket's declared scope. Directly re-measured via frob.gates._arch.arch_gate + frob.gates._waive._apply_waivers against a live build_graph snapshot (not the aggregate JSON summary, which does not decompose per-file) -- confirmed 0 of my 17 files appear in the unwaived LARGE001 set; the 30 remaining unwaived findings repo-wide are all in src/frob/gates/** (T-2369) or src/frob/strata/** (T-2729), both explicitly out of scope for this series" -->