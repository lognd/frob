---
id: T-3342
title: Fix gate:DOC errors (DOC001-007 cluster)
state: done
kind: docs
origin: human
created: '2026-08-29'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/guides/release.md
- docs/index.md
- docs/modules/cli.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: '**/*.py'
  reason: narrow to the exact 16 files this ticket touched for the gate:DOC fix
  actor: logan
  at: '2026-08-29'
- op: remove
  glob: docs/**
  reason: narrow to the exact 16 files this ticket touched for the gate:DOC fix
  actor: logan
  at: '2026-08-29'
- op: remove
  glob: tickets/**
  reason: narrow to the exact 16 files this ticket touched for the gate:DOC fix
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/app/check_runner.py
  reason: narrow to the exact 16 files this ticket touched for the gate:DOC fix
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/app/doctor_runner.py
  reason: narrow to the exact 16 files this ticket touched for the gate:DOC fix
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/ci_report.py
  reason: narrow to the exact 16 files this ticket touched for the gate:DOC fix
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/gates/_comment_placement.py
  reason: narrow to the exact 16 files this ticket touched for the gate:DOC fix
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/gates/_docstring_archaeology.py
  reason: narrow to the exact 16 files this ticket touched for the gate:DOC fix
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/ghio.py
  reason: narrow to the exact 16 files this ticket touched for the gate:DOC fix
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/tickets/_leases.py
  reason: narrow to the exact 16 files this ticket touched for the gate:DOC fix
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/unit/test_app_runners_batch6.py
  reason: narrow to the exact 16 files this ticket touched for the gate:DOC fix
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/unit/test_check.py
  reason: narrow to the exact 16 files this ticket touched for the gate:DOC fix
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/unit/test_close_blocked_by_guard.py
  reason: narrow to the exact 16 files this ticket touched for the gate:DOC fix
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/unit/test_doctor_runner_t1276.py
  reason: narrow to the exact 16 files this ticket touched for the gate:DOC fix
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/unit/test_logging_module.py
  reason: narrow to the exact 16 files this ticket touched for the gate:DOC fix
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/unit/test_reopen_ticket.py
  reason: narrow to the exact 16 files this ticket touched for the gate:DOC fix
  actor: logan
  at: '2026-08-29'
- op: add
  glob: docs/guides/release.md
  reason: narrow to the exact 16 files this ticket touched for the gate:DOC fix
  actor: logan
  at: '2026-08-29'
- op: add
  glob: docs/index.md
  reason: narrow to the exact 16 files this ticket touched for the gate:DOC fix
  actor: logan
  at: '2026-08-29'
- op: add
  glob: docs/modules/cli.md
  reason: narrow to the exact 16 files this ticket touched for the gate:DOC fix
  actor: logan
  at: '2026-08-29'
- op: remove
  glob: src/frob/app/doctor_runner.py
  reason: T-3344 already fixed these 11 files' DOC007 findings independently (re-measured
    0 remain on main); _leases.py split to T-draft-b7982c97 (T-3295 lease collision).
    T-3342 now scoped to exactly the 3 genuinely-unfixed doc files
  actor: logan
  at: '2026-08-29'
- op: remove
  glob: src/frob/ci_report.py
  reason: T-3344 already fixed these 11 files' DOC007 findings independently (re-measured
    0 remain on main); _leases.py split to T-draft-b7982c97 (T-3295 lease collision).
    T-3342 now scoped to exactly the 3 genuinely-unfixed doc files
  actor: logan
  at: '2026-08-29'
- op: remove
  glob: src/frob/gates/_comment_placement.py
  reason: T-3344 already fixed these 11 files' DOC007 findings independently (re-measured
    0 remain on main); _leases.py split to T-draft-b7982c97 (T-3295 lease collision).
    T-3342 now scoped to exactly the 3 genuinely-unfixed doc files
  actor: logan
  at: '2026-08-29'
- op: remove
  glob: src/frob/gates/_docstring_archaeology.py
  reason: T-3344 already fixed these 11 files' DOC007 findings independently (re-measured
    0 remain on main); _leases.py split to T-draft-b7982c97 (T-3295 lease collision).
    T-3342 now scoped to exactly the 3 genuinely-unfixed doc files
  actor: logan
  at: '2026-08-29'
- op: remove
  glob: src/frob/ghio.py
  reason: T-3344 already fixed these 11 files' DOC007 findings independently (re-measured
    0 remain on main); _leases.py split to T-draft-b7982c97 (T-3295 lease collision).
    T-3342 now scoped to exactly the 3 genuinely-unfixed doc files
  actor: logan
  at: '2026-08-29'
- op: remove
  glob: src/frob/tickets/_leases.py
  reason: T-3344 already fixed these 11 files' DOC007 findings independently (re-measured
    0 remain on main); _leases.py split to T-draft-b7982c97 (T-3295 lease collision).
    T-3342 now scoped to exactly the 3 genuinely-unfixed doc files
  actor: logan
  at: '2026-08-29'
- op: remove
  glob: tests/unit/test_app_runners_batch6.py
  reason: T-3344 already fixed these 11 files' DOC007 findings independently (re-measured
    0 remain on main); _leases.py split to T-draft-b7982c97 (T-3295 lease collision).
    T-3342 now scoped to exactly the 3 genuinely-unfixed doc files
  actor: logan
  at: '2026-08-29'
- op: remove
  glob: tests/unit/test_check.py
  reason: T-3344 already fixed these 11 files' DOC007 findings independently (re-measured
    0 remain on main); _leases.py split to T-draft-b7982c97 (T-3295 lease collision).
    T-3342 now scoped to exactly the 3 genuinely-unfixed doc files
  actor: logan
  at: '2026-08-29'
- op: remove
  glob: tests/unit/test_close_blocked_by_guard.py
  reason: T-3344 already fixed these 11 files' DOC007 findings independently (re-measured
    0 remain on main); _leases.py split to T-draft-b7982c97 (T-3295 lease collision).
    T-3342 now scoped to exactly the 3 genuinely-unfixed doc files
  actor: logan
  at: '2026-08-29'
- op: remove
  glob: tests/unit/test_doctor_runner_t1276.py
  reason: T-3344 already fixed these 11 files' DOC007 findings independently (re-measured
    0 remain on main); _leases.py split to T-draft-b7982c97 (T-3295 lease collision).
    T-3342 now scoped to exactly the 3 genuinely-unfixed doc files
  actor: logan
  at: '2026-08-29'
- op: remove
  glob: tests/unit/test_logging_module.py
  reason: T-3344 already fixed these 11 files' DOC007 findings independently (re-measured
    0 remain on main); _leases.py split to T-draft-b7982c97 (T-3295 lease collision).
    T-3342 now scoped to exactly the 3 genuinely-unfixed doc files
  actor: logan
  at: '2026-08-29'
- op: remove
  glob: tests/unit/test_reopen_ticket.py
  reason: T-3344 already fixed these 11 files' DOC007 findings independently (re-measured
    0 remain on main); _leases.py split to T-draft-b7982c97 (T-3295 lease collision).
    T-3342 now scoped to exactly the 3 genuinely-unfixed doc files
  actor: logan
  at: '2026-08-29'
- op: remove
  glob: src/frob/app/check_runner.py
  reason: content reverted earlier due to T-3326 lease collision; scope entry survived
    a git reset --hard main, cleaning up now
  actor: logan
  at: '2026-08-29'
triage_changes:
- field: kind
  old_value: bug
  new_value: docs
  reason: content is exclusively docs/guides/release.md, docs/index.md, docs/modules/cli.md
    -- misclassified as bug at filing time before the T-3344 overlap was discovered
  actor: logan
  at: '2026-08-29'
body_changes:
- mode: append
  reason: 'BUG002 front door (T-2393): purely doc-directive/content fixes for gate:DOC
    findings (frob:tests target-form syntax, frob:doc anchor slug, dead ticket citation,
    stale generated table, orphaned doc link) -- no executable code path changed,
    confirmed via py_compile on every touched .py file'
  actor: logan
  at: '2026-08-29'
  old_length: 136
  new_length: 432
- mode: append
  reason: 'BUG002 front door (T-2393): purely doc-directive/content fixes for gate:DOC
    findings (frob:tests target-form syntax, frob:doc anchor slug, dead ticket citation,
    stale generated table, orphaned doc link) -- no executable code path changed,
    confirmed via py_compile on every touched .py file'
  actor: logan
  at: '2026-08-29'
  old_length: 432
  new_length: 728
- mode: append
  reason: 'BUG002 front door (T-2393): doc-content-only fix (draft ticket citation
    retargeted, orphaned doc linked into index, stale generated CLI table regenerated)
    -- no executable code path changed'
  actor: logan
  at: '2026-08-29'
  old_length: 728
  new_length: 924
- mode: append
  reason: 'BUG002 front door (T-2393): doc-content-only fix (draft ticket citation
    retargeted, orphaned doc linked into index, stale generated CLI table regenerated)
    -- no executable code path changed'
  actor: logan
  at: '2026-08-29'
  old_length: 924
  new_length: 1120
kind_history:
- 2026-08-29 bug->docs evidence=0 done_report=yes
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Series EH: unscoped self-gate DOC cluster at 50 errors. Investigate root causes (rule histogram, archived-ticket doc pointers) then fix.

frob:no-behavior-change reason="purely doc-directive/content fixes for gate:DOC findings (frob:tests target-form syntax, frob:doc anchor slug, dead ticket citation, stale generated table, orphaned doc link) -- no executable code path changed, confirmed via py_compile on every touched .py file"

frob:no-behavior-change reason="purely doc-directive/content fixes for gate:DOC findings (frob:tests target-form syntax, frob:doc anchor slug, dead ticket citation, stale generated table, orphaned doc link) -- no executable code path changed, confirmed via py_compile on every touched .py file"

frob:no-behavior-change reason="doc-content-only fix (draft ticket citation retargeted, orphaned doc linked into index, stale generated CLI table regenerated) -- no executable code path changed"

frob:no-behavior-change reason="doc-content-only fix (draft ticket citation retargeted, orphaned doc linked into index, stale generated CLI table regenerated) -- no executable code path changed"