---
id: T-2825
title: 'LARGE001: split or waive oversized frob.tickets modules, batch 1 of 2'
state: in-progress
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
- src/frob/tickets/_doable.py
- src/frob/tickets/_evidence.py
- src/frob/tickets/_land.py
- src/frob/tickets/_land_finalize.py
- src/frob/tickets/_land_release.py
- src/frob/tickets/_land_squash.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: record BUG002 waiver rationale for a split-or-waive judgment ticket with
    no reproducible defect, mirroring T-2375's own waiver
  actor: logan
  at: '2026-08-21'
  old_length: 1545
  new_length: 2167
designated_repro_test: null
acceptance:
- text: given the batch's 6 files, when frob check --json measures LARGE001, then
    each file reads as severity=note (waived with T-1651-grade reasoning naming why
    no split seam exists) rather than warning
  evidence: []
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

<!-- frob:waive BUG002 reason="this ticket's disposition is split-or-waive judgment calls across 6 already-multiply-split orchestrator/family modules (frob.tickets._doable/_evidence/_land/_land_finalize/_land_release/_land_squash) -- no source code changed and no single reproducible defect exists to bind a failing-at-parent test to; each file was found to be a cohesive family already carved along its real seams by prior tickets (T-1103, T-1171, T-1186, T-1251, T-1334), so the correct closure per T-2375's own body is a frob:waive LARGE001 directive on each file with T-1651-grade reasoning, not a forced split" -->
