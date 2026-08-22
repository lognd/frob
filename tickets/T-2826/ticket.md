---
id: T-2826
title: 'LARGE001: split or waive oversized frob.strata modules (excludes T-2729''s
  _selfconform.py)'
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
- src/frob/strata/__init__.py
- src/frob/strata/_ast.py
- src/frob/strata/_audit.py
- src/frob/strata/_compliance.py
- src/frob/strata/_effects.py
- src/frob/strata/_elaborate.py
- src/frob/strata/_host_isolation.py
- src/frob/strata/_infra.py
- src/frob/strata/_mode_conformance.py
- src/frob/strata/_threat.py
- src/frob/app/_check_chunking.py
- src/frob/app/_check_chunking_baseline.py
evidence_scope:
- tests/test_arch_gate.py
- tests/unit/test_app_runners_batch6.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/app/_check_chunking.py
  reason: T-2369's lease on this file cleared (it re-homed the file to child T-2832,
    now done); T-2830's own dispatch flagged this file as an open, unclaimed LARGE001
    finding -- picking it up here since a lease is free
  actor: logan
  at: '2026-08-21'
- op: add
  glob: src/frob/app/_check_chunking_baseline.py
  reason: 'T-2826''s own split of _check_chunking.py: the --stamp-baseline half moved
    to this new module, a real seam (confirmed via grep -- no external caller reaches
    its internals, only the two run_* entrypoints and budget-side helpers, matching
    git grep evidence in the module''s own docstring)'
  actor: logan
  at: '2026-08-21'
- op: add
  glob: src/frob/app/_check_chunking_baseline.py
  reason: 'T-2826''s own split of _check_chunking.py: the --stamp-baseline half moved
    to this new module, a real seam confirmed via grep before splitting -- no external
    caller reaches its internals, only the two run_* entrypoints and budget-side helpers'
  actor: logan
  at: '2026-08-21'
body_changes:
- mode: append
  reason: BUG002 land-time gate needs this directive for a comment-only waiver pass
    plus one behavior-preserving refactor split
  actor: logan
  at: '2026-08-21'
  old_length: 1545
  new_length: 2237
evidence:
- tests/test_arch_gate.py::TestArchGateLargeFile::test_large_file_fires_large001_warn
- tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_baseline_only_chunk_completes_and_stamps
designated_repro_test: null
acceptance:
- text: given the 10 strata files, when frob check --json runs unbudgeted, then each
    file's LARGE001 finding reads as severity=note (waived, T-1651-grade) except _host_isolation.py
    which reads as waived-with-a-filed-followup for a real seam blocked on out-of-scope
    via-scope migration review (T-2844); given src/frob/app/_check_chunking.py, when
    it is split along its real --stamp-baseline/--budget seam, then both resulting
    files disappear from LARGE001 entirely (no waiver needed) and all existing tests
    (tests/unit/test_check_budget.py, tests/unit/test_check.py) still pass
  evidence:
  - tests/test_arch_gate.py::TestArchGateLargeFile::test_large_file_fires_large001_warn
  - tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_baseline_only_chunk_completes_and_stamps
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

<!-- frob:no-behavior-change reason="T-2826 is a LARGE001 waiver pass (10 strata files, comment-only, no logic change) plus one real refactor: src/frob/app/_check_chunking.py split along its --stamp-baseline/--budget seam into two files, verbatim code movement with zero intended behavior change (T-1616). Verified: tests/unit/test_check_budget.py and tests/unit/test_check.py (152 tests) pass unchanged, plus the designated evidence test directly exercising the moved baseline code (test_stamp_baseline_only_chunk_completes_and_stamps) passes at both main and this ticket's tip, which is expected for a no-behavior-change refactor, not confirmatory-only evidence of an unfixed defect." -->