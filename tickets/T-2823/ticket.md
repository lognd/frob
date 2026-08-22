---
id: T-2823
title: 'LARGE001: split or waive oversized frob.vet/graph/arch modules'
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
- src/frob/vet/_capability_c.py
- src/frob/vet/_capability_core.py
- src/frob/vet/_capability_python.py
- src/frob/vet/_capability_registry/_dangerous_ops_python.py
- src/frob/vet/_capability_registry/_matrix.py
- src/frob/vet/_capability_scan.py
- src/frob/graph/__init__.py
- src/frob/graph/cache.py
- src/frob/graph/callgraph.py
- src/frob/graph/dsl.py
- src/frob/graph/summary.py
- src/frob/arch/_patterns.py
- src/frob/arch/_python.py
- src/frob/arch/_rust.py
evidence_scope:
- tests/test_arch_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: record BUG002 waiver rationale, same shape as T-2825/T-2822
  actor: logan
  at: '2026-08-21'
  old_length: 1545
  new_length: 2329
evidence:
- tests/test_arch_gate.py::TestArchGateLargeFile::test_large_file_fires_large001_warn
designated_repro_test: null
acceptance:
- text: given the batch's 14 files, when frob check --json measures LARGE001, then
    each file reads as severity=note (waived with T-1651-grade reasoning naming why
    no split seam exists) rather than warning
  evidence:
  - tests/test_arch_gate.py::TestArchGateLargeFile::test_large_file_fires_large001_warn
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: de51ede247b5b3af1d7e847e4de1f7eaf6905722
---
Child of T-2375 (LARGE001 burn-down epic). Measured 2026-08-21 via 'frob check --json --budget 500' (severity=warning, code=LARGE001) -- do NOT trust this ticket's own file list without re-measuring first; the tree moves. Each file listed here exceeds frob.toml's max_file_lines=800 threshold.

Per-file disposition is a JUDGMENT CALL, not a mechanical split: T-1651 already established that several LARGE001 files in this repo (_models.py, _waive.py, _land_git_ops.py, check_runner.py, config.py, sys_runner.py -- NOT in this batch, already resolved via frob:waive) are cohesive single-concern files where a line-count split would cut a real seam apart and be STRICTLY WORSE than the warning. For each file in this batch: either (a) find a genuine consumer-set/responsibility seam and split it, or (b) if no real seam exists, add a 'frob:waive LARGE001 reason="..."' with the same rigor T-1651's own waivers show (naming why no split is a real seam, not just 'it is big'). Both are valid closure for a given file; a forced split with no real boundary is not.

Do NOT touch src/frob/strata/_selfconform.py -- it is T-2729's own ticket (largest LARGE001 offender, 2290 lines), already filed, do not absorb it here.

Closure for this CHILD ticket: every file below reads as severity=note (waived) or disappears from LARGE001 entirely when re-measured. Do NOT flip LARGE001 warning->error severity here -- that promotion is T-2375's own final step, deferred until every sibling batch lands (promoting early reds main for siblings' still-open debt).

<!-- frob:waive BUG002 reason="this ticket's disposition is split-or-waive judgment calls across 14 already-cohesive frob.vet/frob.graph/frob.arch modules -- no source code changed and no single reproducible defect exists to bind a failing-at-parent test to; the correct closure per T-2375's own body is a frob:waive LARGE001 directive on each file with T-1651-grade reasoning, not a forced split. Every file in this batch is either already-documented per-language/per-family split residue (T-1420 for vet/, prior ARCH102 waivers for graph/__init__.py and graph/callgraph.py) or a single-engine/single-adapter module with an explicit design constraint against splitting (graph/summary.py's T-0745 'one engine, not two'; arch/_rust.py's one-for-one mirroring of _typescript.py)" -->