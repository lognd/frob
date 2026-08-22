---
id: T-2830
title: 'LARGE001: split or waive oversized frob.app/ticket_runner modules, batch 1
  of 2'
state: queued
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
- src/frob/app/_config_external.py
- src/frob/app/ticket_runner/__init__.py
- src/frob/app/ticket_runner/_close_cmd.py
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/app/ticket_runner/_lifecycle.py
- tickets/T-draft-783d89c8/ticket.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/app/_check_chunking.py
  reason: T-2369 (in-progress) holds an active lease on _check_chunking.py; deferring
    this file, will file follow-up if needed after T-2369 lands
  actor: logan
  at: '2026-08-21'
- op: add
  glob: tickets/T-draft-783d89c8/ticket.md
  reason: SCOPE001 flagged the new follow-up ticket's own file as out-of-scope; it
    is legitimate diff residue from filing that ticket while T-2830 was in-progress
  actor: logan
  at: '2026-08-21'
designated_repro_test: null
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