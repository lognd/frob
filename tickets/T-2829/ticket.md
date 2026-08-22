---
id: T-2829
title: 'LARGE001: split or waive oversized frob.app/ticket_runner modules, batch 2
  of 2'
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
- src/frob/app/ticket_runner/_mutate.py
- src/frob/app/ticket_runner/_new.py
- src/frob/app/ticket_runner/_query.py
- src/frob/app/ticket_runner/_rapid_sweep.py
- src/frob/app/ticket_runner/_verify.py
- src/frob/app/ticket_runner/_waive_audit.py
evidence_scope:
- tests/test_arch_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: BUG002 land-time gate needs this directive for a comment-only waiver change
    with no behavior delta
  actor: logan
  at: '2026-08-21'
  old_length: 1545
  new_length: 1998
evidence:
- tests/test_arch_gate.py::TestArchGateLargeFile::test_large_file_fires_large001_error
designated_repro_test: null
acceptance:
- text: given the 6 in-scope files, when frob check --json runs unbudgeted, then each
    file's LARGE001 finding reads as severity=note (waived) with T-1651-grade per-file
    reasoning naming the specific reason no split seam exists, not a generic size
    waiver
  evidence:
  - tests/test_arch_gate.py::TestArchGateLargeFile::test_large_file_fires_large001_error
evidence_changes:
- old_node: tests/test_arch_gate.py::TestArchGateLargeFile::test_large_file_fires_large001_warn
  new_node: tests/test_arch_gate.py::TestArchGateLargeFile::test_large_file_fires_large001_error
  reason: 'T-2831 renamed this test as part of its intentional WARN-to-ERROR severity
    promotion (same class, same assertion shape: LARGE001 fires on an oversized production
    file); this ticket cited it as general LARGE001-gate-exists evidence, not a claim
    about WARN specifically, so the renamed successor still proves the same property.'
  actor: logan
  at: '2026-08-22'
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 10e407afca90c6aa4e5463e7d69b030414414be4
---
Child of T-2375 (LARGE001 burn-down epic). Measured 2026-08-21 via 'frob check --json --budget 500' (severity=warning, code=LARGE001) -- do NOT trust this ticket's own file list without re-measuring first; the tree moves. Each file listed here exceeds frob.toml's max_file_lines=800 threshold.

Per-file disposition is a JUDGMENT CALL, not a mechanical split: T-1651 already established that several LARGE001 files in this repo (_models.py, _waive.py, _land_git_ops.py, check_runner.py, config.py, sys_runner.py -- NOT in this batch, already resolved via frob:waive) are cohesive single-concern files where a line-count split would cut a real seam apart and be STRICTLY WORSE than the warning. For each file in this batch: either (a) find a genuine consumer-set/responsibility seam and split it, or (b) if no real seam exists, add a 'frob:waive LARGE001 reason="..."' with the same rigor T-1651's own waivers show (naming why no split is a real seam, not just 'it is big'). Both are valid closure for a given file; a forced split with no real boundary is not.

Do NOT touch src/frob/strata/_selfconform.py -- it is T-2729's own ticket (largest LARGE001 offender, 2290 lines), already filed, do not absorb it here.

Closure for this CHILD ticket: every file below reads as severity=note (waived) or disappears from LARGE001 entirely when re-measured. Do NOT flip LARGE001 warning->error severity here -- that promotion is T-2375's own final step, deferred until every sibling batch lands (promoting early reds main for siblings' still-open debt).

<!-- frob:no-behavior-change reason="This ticket is a comment-only LARGE001 waiver pass (T-1651-grade split/waive review) -- all 6 files got a frob:waive LARGE001 directive added, no logic, control flow, or public behavior changed. The designated evidence (test_large_file_fires_large001_warn) passing at both main and this ticket's tip is expected and correct for a no-behavior-change change, not confirmatory-only evidence of an unfixed defect." -->